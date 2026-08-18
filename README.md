# cosmos-discord-faucet
Discord faucet bot for any blockchain based on Cosmos SDK - configured here for Celestia Mocha testnet

<details>
  <summary>List of available commands:</summary>

1. Request coins through the faucet
`/request celestia1vsvx8n7f8dh5udesqqhgrjutyun7zqrgehdq2l`

Transaction status explanation:
✅ - mean bot send transaction to your address

2. Displays the current status of the node where faucet is running
`/faucet_status`

3. Show tap address
`/faucet_address`

4. Show transaction information for a specific transaction ID
`/tx_info 009CEA347EAFD795E8B10088D18156BC15F24362416BEEF1073BFDFD936E19B0`

5. Show address balance
`/balance celestia1vsvx8n7f8dh5udesqqhgrjutyun7zqrgehdq2l`

6. Show address balance in utia
`/balance_utia celestia1vsvx8n7f8dh5udesqqhgrjutyun7zqrgehdq2l`

7. Show available commands
`/help`

</details>


## Requirements
- python3.8+
- Cosmos REST server (LCD)
- Cosmos RPC server

## How to install
1. Run command below
```bash
apt update \
&& apt install -y python3-pip python3-venv git \
&& git clone https://github.com/P-OPSTeam/cosmos-discord-faucet.git \
&& cd cosmos-discord-faucet \
&& python3 -m venv venv \
&& source venv/bin/activate \
&& pip3 install -r requirements.txt
```
2. [Create Discord token](https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token)
3. `cp config.ini.example config.ini` and fill it in (bot token, seed or private key, REST/RPC endpoints, Discord channel names)
4. Invite the bot to your server with the `applications.commands` scope so slash commands register
5. Make sure the chain's REST server is reachable from where the bot runs

## Whitelist
Discord user IDs listed in `discord_wl_ids` (config.ini) get `amount_to_send_wl` per request
instead of the default `amount_to_send`. Leave `discord_wl_ids` empty to disable it.

## How to run
Start faucet bot
```
tmux new -s discord_faucet_bot -d cd ~/cosmos-discord-faucet && source venv/bin/activate && python3 discord_faucet_bot.py
```

### Alternatively, the bot can be run through systemd:
- If necessary, change the username and the path to the script folder in `discord-faucet-bot.service`

- Start the service
```
sudo cp $HOME/cosmos-discord-faucet/discord-faucet-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable discord-faucet-bot.service
sudo systemctl start discord-faucet-bot.service
systemctl status discord-faucet-bot.service
```
