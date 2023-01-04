import logging, disnake, config, os, sys
from disnake.ext import commands
from dotenv import load_dotenv

#Replace this with the one below once your code is live. Once live, changes to commands can take up to 1 hour to sync.
bot = commands.InteractionBot(test_guilds = [os.environ.get("TEST_GUILD_ID")])
#bot = commands.InteractionBot()


#sets up logging using the standard logging library. Configure the level in the config.py file.
def setup_logging():
    try:
        logging.basicConfig(
            format = "%(asctime)s %(levelname)-8s %(message)s",
            filename=f"{config.bot_name}.log",
            encoding="utf-8",
            filemode="w",
            level = config.logging_level,
            datefmt="%Y-%m-%d %H:%M:%S")
        logging.info("-----------")
        print("Setup logging correctly.")

    except Exception as e:
        print(f"ERROR - failed to setup logging - {e}.")
        sys.exit

        
#Alerts once the bot is ready to receive commands
@bot.event
async def on_ready():
    print(f"{config.bot_name} ready.")
    logging.info(f"{config.bot_name} ready.")

    
#called when the bot joins/is invited to a guild.
@bot.event
async def on_guild_join(guild: disnake.Guild):
    
    try:
        #loop through integrations to find who invited us (user object)
        integrations = await guild.integrations()
        for integration in integrations:
            if isinstance(integration, disnake.BotIntegration):
                if integration.application.user.name == bot.user.name:
                    bot_inviter_user = integration.user

        logging.info(f"Got invited to {guild.name} by {bot_inviter_user}.")  
        
    except Exception as e:
        logging.info(f"Got invited to {guild.name}. {e}")  

#called when the bot leaves/is kicked/is banned from a guild.
@bot.event
async def on_guild_remove(guild: disnake.Guild):
    logging.info(f"Left {guild.name}.")
    
    
#An example slash command, will respond World when you use /hello
@bot.slash_command(description="Responds with 'World'")
async def hello(inter: disnake.ApplicationCommandInteraction):

    logging.info(f"{inter.author} said hello.")
    await inter.send("World")
    
    

if __name__ == "__main__":
    load_dotenv()
    setup_logging()
    bot.run(os.environ.get("DISCORD_TEST_TOKEN"))
