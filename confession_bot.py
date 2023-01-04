import logging, disnake, config, os, sys, sqlite3
from disnake.ext import commands
from dotenv import load_dotenv

#Replace this with the one below once your code is live. Once live, changes to commands can take up to 1 hour to sync.
#bot = commands.InteractionBot(test_guilds = [int(os.environ.get("TEST_GUILD_ID"))])
bot = commands.InteractionBot()


#----------------------------------------BOT SETUP----------------------------------------#
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

    except Exception as e:
        print(f"Failed to setup logging. {e}.")
        sys.exit


def setup_db():
    con = sqlite3.connect(config.db)
    cur = con.cursor()

    try:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS channels
            (
                channel_id INTEGER NOT NULL PRIMARY KEY UNIQUE,
                guild_id INTEGER NOT NULL UNIQUE
            )    
        """)

        con.commit()
        con.close()
        logging.info("Setup db ok.")

    except Exception as e:
        logging.exception(f"Unable to set up database. {e}.")
        print(f"Failed to set up database. {e}.")
        sys.exit


#----------------------------------------BOT EVENTS----------------------------------------#        
#Alerts once the bot is ready to receive commands
@bot.event
async def on_ready():
    game = disnake.Game(config.status)
    await bot.change_presence(status = disnake.Status.online, activity = game)
    logging.info(f"{config.bot_name} ready.")


    
#called when the bot joins/is invited to a guild.
@bot.event
async def on_guild_join(guild: disnake.Guild):
    logging.info(f"Got invited to {guild.name}.")


#called when the bot leaves/is kicked/is banned from a guild.
@bot.event
async def on_guild_remove(guild: disnake.Guild):
    logging.info(f"Left {guild.name}.")
    con = sqlite3.connect(config.db) 
    cur = con.cursor()

    try:
        cur.execute("DELETE FROM confessions WHERE guild_id=?",(guild.id,))
        con.commit()
        logging.debug(f"Successfully deleted info about {guild.name} ({guild.id}).")

    except Exception as e:
        logging.exception(f"Failed to remove data about {guild.name} ({guild.id}). {e}")
    
    finally:
        con.close()
        


#----------------------------------------BOT SLASH COMMANDS----------------------------------------#
@bot.slash_command(description="Submit an anonymous confession")
async def confess(
    inter: disnake.ApplicationCommandInteraction,
    confession: str
    ):

    if confession is None:
        await inter.send("You did not enter a confession.", ephemeral=True)
        logging.debug(f"{inter.author} submitted an empty confession.")
    
    else:
        con = sqlite3.connect(config.db)
        cur = con.cursor()
        cur.execute("SELECT channel_id FROM channels WHERE guild_id=?",(inter.guild_id,))

        try:
            channel_id = cur.fetchone()[0]
            confession_channel = inter.guild.get_channel(channel_id)
            
        except Exception as e:
            logging.warning(f"Failed to find {inter.guild_id} in db.")
            await inter.send("Unable to submit your confession, no confessional channel has been setup (run /setup first).", ephemeral=True)
            
        else:
            await confession_channel.send(f"**A new confession**: \n`{confession}`")
            await inter.send("Confession submitted successfully!", ephemeral=True)
            logging.info(f"Successfuly submitted confession.")
        
        finally:
            con.close()




@bot.slash_command(description="Sets up the confession channel. Only for admins.")
async def setup(
    inter: disnake.ApplicationCommandInteraction,
    channel: disnake.TextChannel
    ):

    #the user has the admin permission
    if inter.author.guild_permissions.administrator:
        
        logging.info(f"{inter.author} tried to set up a confessional.")                  
        logging.debug(f"Using {channel.id} for confessional in {inter.guild.name}.")
        con = sqlite3.connect(config.db)
        cur = con.cursor()

        #remove old reference to channel in the guild
        try:
            cur.execute("DELETE FROM channels WHERE guild_id = ?",(inter.guild_id,))
            con.commit()

        except Exception as e:
            logging.debug(f"{inter.guild_id} not found in database. {e}.")
        
        #add new reference to channel in the guild
        finally:            
            cur.execute("INSERT INTO channels VALUES (?,?)",(channel.id, inter.guild_id))
            con.commit()
            con.close()
            await inter.send(f"Successfully set up {channel.mention} as the confessional.", ephemeral=True)

    #user does not have the admin permission
    else:        
        logging.info(f"{inter.author} does not have the admin permission.")
        await inter.send("You don't have permission to use this, you need the administrator permisison.", ephemeral=True)



#----------------------------------------BOT RUN----------------------------------------#
if __name__ == "__main__":
    load_dotenv()
    setup_logging()
    setup_db()
    bot.run(os.environ.get("DISCORD_LIVE_TOKEN"))
