# cosmos-discord-faucet
Discord faucet bot for any blockchain based Cosmos - updated for Celestia Devnet with 0.44 SDK

<details>
  <summary>List of available commands:</summary>

1. Request coins through the faucet  
`$request celes1q3v5cugc8cdpud87u4zwy0a74uxkk6u454rcq9`

Transaction status explanation:  
✅ - mean bot send transaction to your address

2. Displays the current status of the node where faucet is running  
`$faucet_status`

3. Show tap address  
`$faucet_address` or `$tap_address`

4. Show transaction information for a specific transaction ID  
`$tx_info 009CEA347EAFD795E8B10088D18156BC15F24362416BEEF1073BFDFD936E19B0`

5. Show address balance  
`$balance celes1q3v5cugc8cdpud87u4zwy0a74uxkk6u454rcq9`  

</details>  


## Requirements
- python3.6+  
- Cosmos REST server (light-client daemon, a local REST server)  
- Cosmos RPC server  

## How to install  
1. Run command below  
```bash
apt update \
&& apt install -y python3-pip python3-venv git tmux \
&& git clone https://github.com/P-OPSTeam/cosmos-discord-faucet.git \
&& cd cosmos-discord-faucet \
&& python3 -m venv venv \
&& source venv/bin/activate \
&& pip3 install -r requirements.txt
```
2. [Create Discord token](https://github.com/reactiflux/discord-irc/wiki/Creating-a-discord-bot-&-getting-a-token)  
3. Fill in config.ini  
4. Invite the bot to your channel  
5. Make sure Celestia node is running with the REST server enabled
6. Faucet will work only if https://github.com/hukkin/cosmospy/pull/32 is merged. As of May 7th 2022, it wasn't. See Below for the fix

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

### Cosmospy fix

cd ~
git clone https://github.com/hukkin/cosmospy
cd cosmospy
git fetch origin pull/32/head
rm ~/cosmos-discord-faucet/venv/lib/python3.8/site-packages/cosmospy
cp -r cosmospy/src/cosmospy ~/cosmos-discord-faucet/venv/lib/python3.8/site-packages/

