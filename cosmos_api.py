import configparser
import json
from tabulate import tabulate
from mospy import Account, Transaction

c = configparser.ConfigParser()
c.read("config.ini", encoding='utf-8')

# Load data from config
VERBOSE_MODE          = str(c["DEFAULT"]["verbose"])
DECIMAL               = float(c["CHAIN"]["decimal"])
REST_PROVIDER         = str(c["REST"]["provider"])
MAIN_DENOM            = str(c["CHAIN"]["denomination"])
RPC_PROVIDER          = str(c["RPC"]["provider"])
CHAIN_ID              = str(c["CHAIN"]["id"])
BECH32_HRP            = str(c["CHAIN"]["BECH32_HRP"])
GAS_PRICE             = int(c["TX"]["gas_price"])
GAS_LIMIT             = int(c["TX"]["gas_limit"])
FAUCET_PRIVKEY        = str(c["FAUCET"]["private_key"])
FAUCET_SEED           = str(c["FAUCET"]["seed"])
if FAUCET_PRIVKEY == "":
    FAUCET_PRIVKEY = str(Account(seed_phrase=FAUCET_SEED, hrp=BECH32_HRP).private_key.hex())

FAUCET_ADDRESS    = str(Account(private_key=FAUCET_PRIVKEY, hrp=BECH32_HRP).address)
EXPLORER_URL      = str(c["OPTIONAL"]["explorer_url"])

def coins_dict_to_string(coins: dict, table_fmt_: str = "", headers="") -> str:
    if headers == "":
        headers = ["Token", "Amount (wei)", "amount / decimal"]

    hm = []
    """
    :param table_fmt_: grid | pipe | html
    :param coins: {'clink': '100000000000000000000', 'chot': '100000000000000000000'}
    :return: str
    """
    for i in range(len(coins)):
        hm.append([list(coins.keys())[i], list(coins.values())[i], int(int(list(coins.values())[i]) / DECIMAL)])

    print(coins)
    if headers == "no":
        d = tabulate(hm, tablefmt=table_fmt_)
    else:
        d = tabulate(hm, tablefmt=table_fmt_, headers=headers)
    return d


async def async_request(session, url, data: str = ""):
    headers = {"Content-Type": "application/json"}
    try:
        if data == "":
            async with session.get(url=url, headers=headers) as resp:
                data = await resp.text()
        else:
            async with session.post(url=url, data=data, headers=headers) as resp:
                data = await resp.text()

        if type(data) is None or "error" in data:
            return await resp.text()
        else:
            return await resp.json()

    except Exception as err:
        return f'error: in async_request()\n{url} {err}'


async def get_addr_balance_utia(session, addr: str):
    try:
        d = await async_request(session, url=f'{REST_PROVIDER}/cosmos/bank/v1beta1/balances/{addr}')
        if "balances" in str(d):
            for i in d["balances"]:
                if i["denom"] == "utia":
                    return i["amount"]
        else:
            return 0
    except Exception as addr_balancer_err:
        print("get_addr_balance", d, addr_balancer_err)

async def get_addr_balance(session, addr: str):
    d = ""
    coins = {}
    try:
        d = await async_request(session, url=f'{REST_PROVIDER}/cosmos/bank/v1beta1/balances/{addr}')
        if "balances" in str(d):
            for i in d["balances"]:
                coins[i["denom"]] = i["amount"]
            return coins
        else:
            return 0
    except Exception as addr_balancer_err:
        print("get_addr_balance", d, addr_balancer_err)


async def get_address_info(session, addr: str):
    try:
        """:returns sequence: int, account_number: int, coins: dict"""
        d = await async_request(session, url=f'{REST_PROVIDER}/cosmos/auth/v1beta1/accounts/{addr}')
        print(d)

        if "account" in str(d):
            acc_num = int(d["account"]["account_number"])
            try:
                seq     = int(d["account"]["sequence"]) or 0
            except:
                seq = 0
            return seq, acc_num

    except Exception as address_info_err:
        if VERBOSE_MODE == "yes":
            print(address_info_err)
        return 0, 0


async def get_node_status(session):
    url = f'{RPC_PROVIDER}/status'
    return await async_request(session, url=url)


async def get_transaction_info(session, trans_id_hex: str):
    url = f'{REST_PROVIDER}/cosmos/tx/v1beta1/txs/{trans_id_hex}'
    resp = await async_request(session, url=url)
    if 'height' in str(resp):
        return resp
    else:
        return f"error: {trans_id_hex} not found. Either non existent or not yet added to the chain"


async def send_tx(session, recipient: str, denom_lst: list, amount: list) -> str:
    url_ = f'{REST_PROVIDER}/cosmos/tx/v1beta1/txs'
    try:
        sequence, acc_number = await get_address_info(session, FAUCET_ADDRESS)
        txs = await gen_transaction(recipient_=recipient, sequence=sequence,
                                    account_num=acc_number, denom=denom_lst, amount_=amount)
        tx_bytes = txs.get_tx_bytes_as_string()
        pushable_tx = json.dumps(
              {
                "tx_bytes": tx_bytes,
                "mode": "BROADCAST_MODE_SYNC" # Available modes: BROADCAST_MODE_SYNC, BROADCAST_MODE_ASYNC, BROADCAST_MODE_BLOCK
              }
            )
        # send the request
        print("tx data:" + pushable_tx)
        result = async_request(session, url=url_, data=pushable_tx)
        return await result

    except Exception as reqErrs:
        if VERBOSE_MODE == "yes":
            print(f'error in send_txs() {REST_PROVIDER}: {reqErrs}')
        return f"error: {reqErrs}"

async def send_tx2(session, recipient: str, denom_lst: list, amount: list, sequence: int) -> str:
    url_ = f'{REST_PROVIDER}/cosmos/tx/v1beta1/txs'
    try:
        seqnotused, acc_number = await get_address_info(session, FAUCET_ADDRESS)
        txs = await gen_transaction(recipient_=recipient, sequence=sequence,
                                    account_num=acc_number, denom=denom_lst, amount_=amount)
        tx_bytes = txs.get_tx_bytes_as_string()
        pushable_tx = json.dumps(
              {
                "tx_bytes": tx_bytes,
                "mode": "BROADCAST_MODE_SYNC" # Available modes: BROADCAST_MODE_SYNC, BROADCAST_MODE_ASYNC, BROADCAST_MODE_BLOCK
              }
            )
        # send the request
        print("tx data retried:" + pushable_tx)
        result = async_request(session, url=url_, data=pushable_tx)
        return await result

    except Exception as reqErrs:
        if VERBOSE_MODE == "yes":
            print(f'error in send_txs() {REST_PROVIDER}: {reqErrs}')
        return f"error: {reqErrs}"

async def gen_transaction(recipient_: str, sequence: int, denom: list, account_num: int, amount_: list,
                          gas: int = GAS_LIMIT, memo: str = "", chain_id_: str = CHAIN_ID,
                          fee: int = GAS_PRICE, priv_key: str = FAUCET_PRIVKEY):

    account = Account(
        private_key=priv_key,
        account_number=account_num,
        next_sequence=sequence,
        hrp=BECH32_HRP
    )
    tx = Transaction(
        account=account,
        gas=gas,
        memo=memo,
        chain_id=chain_id_
    )
    tx.set_fee(amount=fee, denom=MAIN_DENOM)
    if type(denom) is list:
        for i, den in enumerate(denom):
            tx.add_send_msg(recipient=recipient_, amount=amount_[i], denom=den)
    else:
        tx.add_send_msg(recipient=recipient_, amount=amount_[0], denom=denom[0])
    return tx

def gen_keypair():
    """:returns address: str, private_key: str, seed: str"""
    new_account = Account(hrp=BECH32_HRP)
    return new_account.address, new_account.private_key.hex(), new_account.seed_phrase
