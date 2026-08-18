from asyncio import sleep
import aiofiles as aiof
import aiohttp
import discord
from discord import app_commands
from mospy import Account
import configparser
import logging
import time
import datetime
import sys
import cosmos_api as api
import os.path
from os import path
import json
import re

print('Version 0.2.0')

# Turn Down Discord Logging
disc_log = logging.getLogger('discord')
disc_log.setLevel(logging.INFO)

# Configure Logging
logging.basicConfig(stream=sys.stdout, level=logging.CRITICAL)
logger = logging.getLogger(__name__)

# Load config
c = configparser.ConfigParser()
c.read("config.ini", encoding='utf-8')

VERBOSE_MODE       = str(c["DEFAULT"]["verbose"])
BECH32_HRP         = str(c["CHAIN"]["BECH32_HRP"])
DECIMAL            = float(c["CHAIN"]["decimal"])
DENOMINATION_LST   = c["TX"]["denomination_list"].split(",")
AMOUNT_TO_SEND_LST = c["TX"]["amount_to_send"].split(",")
AMOUNT_TO_SEND_WL  = c["TX"].get("amount_to_send_wl", c["TX"]["amount_to_send"]).split(",")
FAUCET_SEED        = str(c["FAUCET"]["seed"])
FAUCET_PRIVKEY     = str(c["FAUCET"]["private_key"])
if FAUCET_PRIVKEY == "":
    FAUCET_PRIVKEY = str(Account(seed_phrase=FAUCET_SEED, hrp=BECH32_HRP).private_key.hex())
FAUCET_ADDRESS     = str(Account(private_key=FAUCET_PRIVKEY, hrp=BECH32_HRP).address)
EXPLORER_URL       = str(c["OPTIONAL"]["explorer_url"])
if EXPLORER_URL != "":
    EXPLORER_URL = f'{EXPLORER_URL}/transactions/'
REQUEST_TIMEOUT    = int(c["FAUCET"]["request_timeout"])
TOKEN              = str(c["FAUCET"]["discord_bot_token"])
LISTENING_CHANNELS = list(c["FAUCET"]["channels_to_listen"].split(","))
WL_DISCORD_IDS     = list(c["FAUCET"].get("discord_wl_ids", "").split(","))

APPROVE_EMOJI = "✅"
REJECT_EMOJI = "🚫"
ACTIVE_REQUESTS = {}

# No message_content intent needed — slash commands receive arguments directly
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

with open("help-msg.txt", "r", encoding="utf-8") as help_file:
    help_msg = help_file.read()

print(f'Faucet address :{FAUCET_ADDRESS}')
print(f'Loading active requests')
if path.exists("active-requests.json") \
    and os.stat("active-requests.json").st_size != 0:
    with open("active-requests.json", "r", encoding="utf-8") as json_file:
        ACTIVE_REQUESTS = json.load(json_file)
    print(f'Active request file loaded')
else:
    print(f'No active requests file')


async def save_transaction_statistics(some_string: str):
    async with aiof.open("transactions.csv", "a") as csv_file:
        await csv_file.write(f'{some_string}\n')
        await csv_file.flush()

async def save_active_requests():
    async with aiof.open("active-requests.json", "w") as json_file:
        await json_file.write(json.dumps(ACTIVE_REQUESTS))
        await json_file.flush()


def in_faucet_channel(interaction: discord.Interaction) -> bool:
    return interaction.channel is not None and interaction.channel.name in LISTENING_CHANNELS


@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message(
            "This command is only available in the faucet channel.", ephemeral=True)
    else:
        raise error


@client.event
async def on_ready():
    await tree.sync()
    logger.info(f'Logged in as {client.user}')
    print(f'Logged in as {client.user}, slash commands synced.')


@tree.command(name="balance", description="Show address balance")
@app_commands.check(in_faucet_channel)
async def balance(interaction: discord.Interaction, address: str):
    await interaction.response.defer()
    session = aiohttp.ClientSession()
    address = address.replace(" ", "").lower()
    if str(address[:8]) == BECH32_HRP and len(address) == 47:
        coins = await api.get_addr_balance(session, address)
        if len(coins) >= 1:
            await interaction.followup.send(
                f'{interaction.user.mention}\n'
                f'```{api.coins_dict_to_string(coins, headers="no")}```')
        else:
            await interaction.followup.send(
                f'{interaction.user.mention} account is not initialized (balance is empty) or rpc call failed')
    else:
        await interaction.followup.send(
            f'{interaction.user.mention}, Invalid address format `{address}`')
    await session.close()


@tree.command(name="balance_utia", description="Show address balance in utia")
@app_commands.check(in_faucet_channel)
async def balance_utia(interaction: discord.Interaction, address: str):
    await interaction.response.defer()
    session = aiohttp.ClientSession()
    address = address.replace(" ", "").lower()
    if str(address[:8]) == BECH32_HRP and len(address) == 47:
        coins = await api.get_addr_balance_utia(session, address)
        await interaction.followup.send(f'{interaction.user.mention}, balance is {coins} utia\n')
    else:
        await interaction.followup.send(
            f'{interaction.user.mention}, Invalid address format `{address}`')
    await session.close()


@tree.command(name="help", description="Show available commands")
@app_commands.check(in_faucet_channel)
async def help_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(help_msg)


@tree.command(name="faucet_status", description="Show current node synchronization status")
@app_commands.check(in_faucet_channel)
async def faucet_status(interaction: discord.Interaction):
    await interaction.response.defer()
    print(interaction.user.name, "status request")
    session = aiohttp.ClientSession()
    try:
        s = await api.get_node_status(session)
        coins = await api.get_addr_balance(session, FAUCET_ADDRESS)
        seq, acc_num = await api.get_address_info(session, FAUCET_ADDRESS)
        if "node_info" in str(s) and "error" not in str(s):
            s = (f'```'
                 f'Moniker:       {s["result"]["node_info"]["moniker"]}\n'
                 f'Address:       {FAUCET_ADDRESS}\n'
                 f'Syncs?:        {s["result"]["sync_info"]["catching_up"]}\n'
                 f'Last block:    {s["result"]["sync_info"]["latest_block_height"]}\n'
                 f'Voting power:  {s["result"]["validator_info"]["voting_power"]}\n'
                 f'Sequence:      {seq}\n'
                 f'Coins:\n{api.coins_dict_to_string(coins, headers="no")}```')
            await interaction.followup.send(s)
        else:
            await interaction.followup.send(f'Node status unavailable. RPC response:\n```{str(s)[:300]}```')
    except Exception as statusErr:
        print(statusErr)
        await interaction.followup.send(f'Error fetching node status: `{str(statusErr)[:200]}`')
    await session.close()


@tree.command(name="faucet_address", description="Show faucet wallet address")
@app_commands.check(in_faucet_channel)
async def faucet_address(interaction: discord.Interaction):
    await interaction.response.send_message(FAUCET_ADDRESS)


@tree.command(name="tx_info", description="Show transaction information for a given hash")
@app_commands.check(in_faucet_channel)
async def tx_info(interaction: discord.Interaction, hash_id: str):
    await interaction.response.defer()
    session = aiohttp.ClientSession()
    hash_id = hash_id.replace(" ", "")
    try:
        if len(hash_id) == 64:
            tx = await api.get_transaction_info(session, hash_id)
            if "amount" and "fee" in str(tx):
                from_        = tx["tx"]["body"]["messages"][0]["from_address"]
                to_          = tx["tx"]["body"]["messages"][0]["to_address"]
                sended_coins = {}
                for tx_ in tx["tx"]["body"]["messages"]:
                    sended_coins.update({tx_["amount"][0]["denom"]: tx_["amount"][0]["amount"]})
                raw_log = tx["tx_response"]["raw_log"]
                tx_text = (f'```'
                           f'From:    {from_}\n'
                           f'To:      {to_}\n'
                           f'{api.coins_dict_to_string(sended_coins, headers="no")}```\n'
                           f'> raw_log:'
                           f'```{raw_log}```\n')
                embed = discord.Embed(title="Tx info", url="https://www.pops.one",
                                      description=tx_text, color=discord.Color.blue())
                embed.set_footer(text="Faucet brought to you by the POPS Team - https://www.pops.one/")
                await interaction.followup.send(embed=embed)
            else:
                await interaction.followup.send(f'{interaction.user.mention}, `{tx}`')
        else:
            await interaction.followup.send(
                f'Incorrect length hash id: {len(hash_id)} instead 64')
    except Exception as tx_infoErr:
        print(tx_infoErr)
        await interaction.followup.send("Can't get transaction info")
    await session.close()


@tree.command(name="embedtest", description="Test embed display for a transaction hash")
@app_commands.check(in_faucet_channel)
async def embedtest(interaction: discord.Interaction, hash_id: str):
    await interaction.response.defer()
    session = aiohttp.ClientSession()
    hash_id = hash_id.replace(" ", "")
    coins = await api.get_addr_balance(session, FAUCET_ADDRESS)
    if len(hash_id) == 64:
        tx = await api.get_transaction_info(session, hash_id)
        if "amount" and "fee" in str(tx):
            from_        = tx["tx"]["body"]["messages"][0]["from_address"]
            to_          = tx["tx"]["body"]["messages"][0]["to_address"]
            sended_coins = {}
            for tx_ in tx["tx"]["body"]["messages"]:
                sended_coins.update({tx_["amount"][0]["denom"]: tx_["amount"][0]["amount"]})
            raw_log = tx["tx_response"]["raw_log"]
            tx_text = (f'```'
                       f'From:    {from_}\n'
                       f'To:      {to_}\n'
                       f'{api.coins_dict_to_string(sended_coins, headers="no")}```\n'
                       f'> raw_log:'
                       f'```{raw_log}```\n')
            embed = discord.Embed(title="Tx info", url="https://www.pops.one",
                                  description=tx_text, color=discord.Color.blue())
            embed.set_footer(text="Faucet brought to you by the POPS Team - https://www.pops.one/")
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send(f'Transaction not found or not yet on chain: `{hash_id}`')
    else:
        await interaction.followup.send(f'Incorrect hash length: {len(hash_id)} chars (expected 64)')
    await session.close()


@tree.command(name="request", description="Request testnet tokens from the faucet")
@app_commands.check(in_faucet_channel)
async def request(interaction: discord.Interaction, address: str):
    await interaction.response.defer()
    session = aiohttp.ClientSession()
    message_timestamp = time.time()
    requester = interaction.user
    requester_address = address.replace(" ", "").lower()

    print(f"{requester.id} requested fund for {requester_address}")
    print(f"active requests: no longer shown")
    print(f"Verify Address format")

    if len(requester_address) != 47 or requester_address[:8] != BECH32_HRP:
        await interaction.followup.send(
            f'{requester.mention}, Invalid address format `{requester_address}`\n'
            f'Address length must be equal 47 and the suffix must be `{BECH32_HRP}`')
        print(f"{requester.id} requested for {requester_address} with wrong format")
        await session.close()
        return

    # Remove from active requests if address has no balance/transactions yet
    if str(requester.id) in ACTIVE_REQUESTS and ACTIVE_REQUESTS[str(requester.id)]["address"] == requester_address:
        coins = await api.get_addr_balance(session, requester_address)
        seq, acc_num = await api.get_address_info(session, requester_address)
        if not isinstance(coins, int) and len(coins) == 0 and seq == 0:
            print(f"{requester_address} had no transaction and no a balance of 0, let's remove from active-request file")
            del ACTIVE_REQUESTS[str(requester.id)]

    # Check if the faucet timeout has reached for this discord user
    if str(requester.id) in ACTIVE_REQUESTS:
        check_time = ACTIVE_REQUESTS[str(requester.id)]["next_request"]
        print(f"Checking {requester.id} last requests")
        if check_time > message_timestamp:
            timeout_in_hours = int(REQUEST_TIMEOUT) / 60 / 60
            please_wait_text = (f'{requester.mention}, You can request coins no more than once every {timeout_in_hours} hours. '
                                f'The next attempt is possible after '
                                f'{round((check_time - message_timestamp) / 60, 2)} minutes')
            await interaction.followup.send(please_wait_text)
            print(f"{requester.id} requested for {requester_address} too early")
            await session.close()
            return
        else:
            print(f"Allow {requester.id} to send fund")
            del ACTIVE_REQUESTS[str(requester.id)]

    # Check if the address already received fund from another discord user
    for key in ACTIVE_REQUESTS.keys():
        if str(requester_address) in ACTIVE_REQUESTS[key].values():
            await interaction.followup.send(f'{requester_address} already received fund')
            print(f"{requester_address} already received fund from another user")
            await session.close()
            return

    if str(requester.id) not in ACTIVE_REQUESTS:
        coins = await api.get_addr_balance(session, FAUCET_ADDRESS)
        seq, acc_num = await api.get_address_info(session, FAUCET_ADDRESS)
        old_requester_balance = await api.get_addr_balance_utia(session, requester_address)
        print(f"old requester balance: {old_requester_balance}")
        coins = {i: coins[i] for i in coins if int(coins[i]) > int(AMOUNT_TO_SEND_LST[0])}
        amount_to_send = AMOUNT_TO_SEND_LST[0] if str(requester.id) not in WL_DISCORD_IDS else AMOUNT_TO_SEND_WL[0]

        transaction = await api.send_tx(session, recipient=requester_address,
                                        denom_lst=list(coins.keys()),
                                        amount=[amount_to_send] * len(list(coins.keys())))
        logger.info(f'Transaction result:\n{transaction}')
        print(f'Transaction result:\n{transaction}')

        if "txhash" in str(transaction) and "code" in str(transaction) and transaction["tx_response"]["code"] == 0:
            if str(requester.id) not in WL_DISCORD_IDS:
                ACTIVE_REQUESTS[str(requester.id)] = {
                    "address": requester_address,
                    "next_request": message_timestamp + REQUEST_TIMEOUT}
                embed = discord.Embed(title="Request fund", url="https://www.pops.one",
                                      description=(f'{requester.mention}, `{EXPLORER_URL}{transaction["tx_response"]["txhash"]}` '
                                                   f'pending insertion into a block, you can verify by using /tx_info command\n'),
                                      color=discord.Color.blue())
                embed.set_footer(text="Faucet brought to you by the POPS Team - https://www.pops.one/")
                await interaction.followup.send(embed=embed)
                await save_active_requests()
            else:
                embed = discord.Embed(title="Request fund", url="https://www.pops.one",
                                      description=(f'{requester.mention}, `{EXPLORER_URL}{transaction["tx_response"]["txhash"]}` '
                                                   f'pending insertion into a block\n'),
                                      color=discord.Color.blue())
                await interaction.followup.send(embed=embed)
        else:
            if "account sequence mismatch" in str(transaction):
                x = re.search("expected (\d+)", str(transaction))
                if x:
                    print(f"match new seq: {x[1]}")
                    newsequence = int(x[1])
                    transaction = await api.send_tx2(session, recipient=requester_address,
                                                     denom_lst=list(coins.keys()),
                                                     amount=[AMOUNT_TO_SEND_LST[0]] * len(list(coins.keys())),
                                                     sequence=newsequence)
                    logger.info(f'Transaction result:\n{transaction}')
                    print(f'Transaction result:\n{transaction}')
                    if "txhash" in str(transaction) and "code" in str(transaction) and transaction["tx_response"]["code"] == 0:
                        ACTIVE_REQUESTS[str(requester.id)] = {
                            "address": requester_address,
                            "next_request": message_timestamp + REQUEST_TIMEOUT}
                        embed = discord.Embed(title="Request fund", url="https://www.pops.one",
                                              description=(f'{requester.mention}, `{EXPLORER_URL}{transaction["tx_response"]["txhash"]}` '
                                                           f'pending insertion into a block, you can verify by using /tx_info command\n'),
                                              color=discord.Color.blue())
                        embed.set_footer(text="Faucet brought to you by the POPS Team - https://www.pops.one/")
                        await interaction.followup.send(embed=embed)
                        await save_active_requests()
            else:
                await interaction.followup.send(
                    f"{requester.mention}, Can't send transaction. Try making another request")

        now = datetime.datetime.now()
        await save_transaction_statistics(f'{transaction};{now.strftime("%Y-%m-%d %H:%M:%S")}')

    await session.close()


client.run(TOKEN)
