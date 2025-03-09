import discord
from xrpl.wallet import Wallet
from xrpl.core.keypairs import generate_seed
import xrpl.transaction
from xrpl.models.transactions import Payment, Memo
from xrpl.utils import str_to_hex
from discord.ext import commands, tasks
from xrpl.asyncio.clients import AsyncJsonRpcClient
from datetime import datetime, timedelta
import CommonFunction as cf
import Settings as s

cycle_counter = 0

# Load all registered discord users from the database
DiscordUser = cf.ExecuteSQLQuery("""          
       SELECT u.[UserKey]
      ,u.[ID]
      ,u.[Name]
	  ,ISNULL(u.[Address],'') AS Address
      ,u.[Seed]
	  FROM [discord].[tbl_User] u""")

#Discord bot initialization
intents = discord.Intents.default()
intents.message_content = True 
intents.dm_messages = True 
client = commands.Bot(command_prefix='!', intents=intents)
tree = client.tree

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    try:
        synced = await tree.sync()
        print(f'Synced {len(synced)} command(s)')
        get_transactions.start()
    except Exception as e:
        print(e) 


#Get answer messages from the database and send them to users every 10 seconds
@tasks.loop(seconds=10)
async def get_transactions():
    global cycle_counter
    cycle_counter = cycle_counter + 1
    print('Working... cycle number ', cycle_counter, 'started')
        
    cf.ExecuteSQLQuery("{CALL [discord].[sp_Message]()}")

    PFNodeMessage = cf.ExecuteSQLQuery(f"""SELECT
            u.ID,
            m.[MessageKey],
            m.[Text]
            FROM [discord].[tbl_Message] m
            INNER JOIN discord.tbl_User u ON u.UserKey=m.UserKey
            WHERE Status='Created' AND Type='Answering' AND m.Timestamp>={s.StartTimestamp}
            ORDER BY Timestamp""")
   
    for Message in PFNodeMessage:

        user = await client.fetch_user(int(Message.ID))
        await user.send(Message.Text)
        cf.ExecuteSQLQuery("UPDATE [discord].tbl_Message SET Status='Processed' WHERE MessageKey= ?", (Message.MessageKey))
    print('Working... cycle number', cycle_counter, 'finished')



#Get new messages from users and send them to Forecaster Node     
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if isinstance(message.channel, discord.DMChannel):
        User = next((User for User in DiscordUser if User.ID == str(message.author.id)), None)
        if User is not None:
            if User.Address!='':
                try:
                    RippleClient = AsyncJsonRpcClient(s.BCNodeURL)
                    wallet = Wallet.from_secret(User.Seed)
                    payment = Payment(
                        account=User.Address,
                        amount="1",
                        destination=s.PolyMarketForecasterNodeAddress,
                        memos=[Memo(memo_data=str_to_hex(message.content[:1000]))]
                    )

                    
                    response = await xrpl.asyncio.transaction.submit_and_wait(payment, RippleClient, wallet)
                except Exception:
                    await message.channel.send('Transaction submit error, please check your wallet and try again')
                    cf.EventLog('DiscordFrontend.py','Exception','Transaction submit error, please check your wallet and try again',str(Exception),[str(response),str(payment),str(wallet)])
                else:
                    cf.ExecuteSQLQuery("{CALL [discord].[sp_NewAskingMessage] (?, ?, ?, ?)}", (User.UserKey,response.result["hash"],message.content[:1000],s.PolyMarketForecasterNodeKey))
            else:
                await message.channel.send('Please register your wallet with /fc_create_wallet or /fc_store_seed')
        else:
            await message.channel.send('Please register your wallet with /fc_create_wallet or /fc_store_seed')
    else:
        await client.process_commands(message)    

#Generate new wallet for the user
@tree.command(name="fc_create_wallet", description="Setup your XRP wallet")
async def set_wallet(interaction: discord.Interaction):
    seed = generate_seed()
    wallet = Wallet.from_secret(seed)

    class WalletInfoModal(discord.ui.Modal, title='Setup your XRP wallet'):
        def __init__(self, client):
            super().__init__()
            self.client = client

        address1 = discord.ui.TextInput(
            label='Address (do not modify)',
            default=wallet.classic_address,
            style=discord.TextStyle.short,
            required=True
        )
        seed1 = discord.ui.TextInput(
            label='Secret (do not modify)',
            default=wallet.seed,
            style=discord.TextStyle.short,
            required=True
        )

        async def on_submit(self, interaction: discord.Interaction):
            global DiscordUser
            User = next((User for User in DiscordUser if User.ID == str(interaction.user.id)), None)
            if User is None:
                cf.ExecuteSQLQuery("{CALL [discord].[sp_UpdateUser] (NULL, ?, ?, ?, ?)}", ( str(interaction.user.id), str(interaction.user.name), str(wallet.classic_address), str(wallet.seed)))
            
                DiscordUser = cf.ExecuteSQLQuery("""          
                                                    SELECT u.[UserKey]
                                                    ,u.[ID]
                                                    ,u.[Name]
                                                    ,ISNULL(u.[Address],'') AS Address
                                                    ,u.[Seed]
                                                    FROM [discord].[tbl_User] u""")
                await interaction.response.send_message(f"Wallet {wallet.classic_address} set successfully. Deposit 2 XRP to your wallet (1 XRP to activate, 1 XRP to use for gas). {s.DiscordWelcomeMessage}",ephemeral=True)
                                                                
            else:
                User.Address = str(wallet.classic_address)
                User.Seed = str(wallet.seed)
                cf.ExecuteSQLQuery("{CALL [discord].[sp_UpdateUser] (?, ?, ?, ?, ?)}", (User.UserKey, User.ID, User.Name, User.Address, User.Seed))
            
        
                await interaction.response.send_message(f"Wallet {User.Address} set successfully. Deposit 2 XRP to your wallet (1 XRP to activate, 1 XRP to use for gas)",ephemeral=True)
   

    # Create the modal with the client reference and send it
    modal = WalletInfoModal(interaction.client)
    await interaction.response.send_modal(modal)

#Import user's address and secret to the bot   
@tree.command(name="fc_store_seed", description="Import your address and secret to the bot")
async def store_seed(interaction: discord.Interaction):


    class StoreSeedModal(discord.ui.Modal, title='Import your XRP wallet'):
        def __init__(self, client):
            super().__init__()
            self.client = client

        seed = discord.ui.TextInput(
            label='Secret',
            default='',
            style=discord.TextStyle.short,
            required=True
        )

        async def on_submit(self, interaction: discord.Interaction):
            global DiscordUser
            wallet = Wallet.from_secret(self.seed.value)
            User = next((User for User in DiscordUser if User.ID == str(interaction.user.id)), None)
            if User is None:
                cf.ExecuteSQLQuery("{CALL [discord].[sp_UpdateUser] (NULL, ?, ?, ?, ?)}", ( str(interaction.user.id), str(interaction.user.name), str(wallet.classic_address), str(wallet.seed)))
            
                DiscordUser = cf.ExecuteSQLQuery("""          
                                                    SELECT u.[UserKey]
                                                    ,u.[ID]
                                                    ,u.[Name]
                                                    ,ISNULL(u.[Address],'') AS Address
                                                    ,u.[Seed]
                                                    FROM [discord].[tbl_User] u""")
                await interaction.response.send_message(f"Wallet {wallet.classic_address} set successfully. Deposit 2 XRP to your wallet (1 XRP to activate, 1 XRP to use for gas). {s.DiscordWelcomeMessage}",ephemeral=True)
                                                                
            else:
                User.Address = str(wallet.classic_address)
                User.Seed = str(self.seed.value)
                cf.ExecuteSQLQuery("{CALL [discord].[sp_UpdateUser] (?, ?, ?, ?, ?)}", (User.UserKey, User.ID, User.Name, User.Address, User.Seed))
            
        
                await interaction.response.send_message(f"Wallet {User.Address} set successfully. Deposit 2 XRP to your wallet (1 XRP to activate, 1 XRP to use for gas)",ephemeral=True)
            
    
    modal = StoreSeedModal(interaction.client)
    await interaction.response.send_modal(modal)

#Show user's address and secret
@tree.command(name="fc_my_wallet", description="Show your XRP address and secret")
async def show_wallet(interaction: discord.Interaction):
    User = next((User for User in DiscordUser if User.ID == str(interaction.user.id)), None)
    if User is None:
        await interaction.response.send_message(
                "Unregistered user. Please register with /fc_create_wallet command",
                ephemeral=True
            )
    else:
        
        class PrivateKeyModal(discord.ui.Modal, title='Wallet information'):
            def __init__(self, client):
                super().__init__()
                self.client = client
    
            address = discord.ui.TextInput(
                label='Your address',
                default=User.Address,
                style=discord.TextStyle.short,
                required=True
                )
            seed = discord.ui.TextInput(
                label='Your secret (do not share!)',
                default=User.Seed,
                style=discord.TextStyle.short,
                required=True
                )
            
            async def on_submit(self, interaction: discord.Interaction):
                await interaction.response.send_message(
                    "Wallet was shown",
                    ephemeral=True
                )
        
        # Create the modal with the client reference and send it
        modal = PrivateKeyModal(interaction.client)
        await interaction.response.send_modal(modal)

#Reset user's context. To do: send it as command inside memo instead of direct access to the backend database    
@tree.command(name="fc_reset_context", description="Reset dialogue")
async def show_wallet(interaction: discord.Interaction):
    User = next((User for User in DiscordUser if User.ID == str(interaction.user.id)), None)
    cf.ExecuteSQLQuery("""{CALL [pfn].[sp_UpdateUserNodeSetting] (?, ?, NULL,NULL)}""", (User.Address, s.PolyMarketForecasterNodeAddress)) 
    await interaction.response.send_message(
                "New dialogue is started. DM bot to start conversation",
                ephemeral=True
            )
    
#Select Flux API mode and store it as user address setting. To do: send it as command inside memo instead of direct access to the backend database
@tree.command(name="fc_select_mode", description="Select light or full mode")
async def select_mode(interaction: discord.Interaction):
    User = next((User for User in DiscordUser if User.ID == str(interaction.user.id)), None)
    if User is None:
        await interaction.response.send_message(
                "Unregistered user. Please register with /fc_create_wallet command",
                ephemeral=True
            )
    else:
        class ModeSelection(discord.ui.View):
            @discord.ui.select(
            placeholder="Select app mode",
            min_values=1,
            max_values=1,
            options=[
                discord.SelectOption(label="Light", description="Quick analysis (~30 sec for answer)"),
                discord.SelectOption(label="Full", description="Deep analysis (~3 min for answer)"),
                discord.SelectOption(label="Full with research", description="Deep analysis with full research (~3 min for answer)"),
            ])
            async def combo_box_select(self, select: discord.ui.Select, interaction: discord.Interaction):
                cf.ExecuteSQLQuery("""{CALL [pfn].[sp_UpdateUserNodeSetting] (?, ?, ?,NULL)}""", (User.Address, s.PolyMarketForecasterNodeAddress, interaction.values[0]))
                await select.response.send_message(f"[{interaction.values[0]}] mode is set. Context was reset",ephemeral=True)
        View = ModeSelection()
        await interaction.response.send_message(
        content="Select app mode:",
        view=View,
        ephemeral=True 
            )

#Start the bot
client.run(s.DiscordAppToken)
