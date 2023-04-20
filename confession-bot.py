import logging, disnake, config, sys, sqlite3, tokens
from disnake.ext import commands

#Replace this with the one below once your code is live. Once live, changes to commands can take up to 1 hour to sync.
#bot = commands.InteractionBot(test_guilds = [config.test_guild_id])
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

    if confession is None or confession == "" or len(confession) == 0:
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
            await inter.send("Unable to submit your confession, no confessional channel has been setup (admins need to run /setup first).", ephemeral=True)
            
        else:
            await confession_channel.send(f"**A new confession has been submitted**: \n`{confession}`")
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

#########################################################################################
#    INFO FUNCTIONS BELOW



@bot.slash_command(description="Info about the bot.")
async def info(
    inter: disnake.ApplicationCommandInteraction,
    hidden: bool = commands.Param(default = False, description = "Whether to hide this from others or not.")
    ):

        logging.info(f"{inter.author} checked bot info.")  

        info_embed = disnake.Embed(title="Space Bot Info")
        info_embed.add_field(name="Version", value=config.script_version + " - " + config.script_date, inline=True)
        info_embed.add_field(name="Joined servers", value=len(bot.guilds), inline=True)
        info_embed.add_field(name="Discord Support Server", value=config.discord_server, inline=False)
        info_embed.add_field(name="Bot Invite Link", value=config.invite_link_short, inline=False)
        info_embed.add_field(name="Bot Code on Github", value=config.github_link, inline=False)
               
        await inter.send(embed=info_embed, ephemeral=hidden)




#########################################################################################
#    SECRET FUNCTIONS BELOW
    
@bot.slash_command(description="Super Secret")
async def server_info(
    inter: disnake.ApplicationCommandInteraction,
    short: bool = commands.Param(default=True, description="Show only the latest 10 joined servers, or the full info.")
    ):
    
    #only the bot owner can use this command
    if inter.author == bot.owner:   
        
        joined_guilds = []
        guild_count = len(bot.guilds)
        

        for guild in bot.guilds:
            #gather guild info in a tuple in a list(?) so we can sort by joined date in the embed.
            join_date = guild.me.joined_at
            join_date = join_date.strftime("%Y-%m-%d %H:%M:%S")
            joined_guilds.append((join_date, guild.name, guild.member_count))            
        
        #sorting the guilds by join date newest to oldest
        joined_guilds.sort(key = lambda tup: tup[0], reverse=True) # from https://stackoverflow.com/questions/3121979/
        
        
        
        if short == True:
        #only show the 10 most recently joined guilds
            guild_embed = disnake.Embed(title="Joined Server Info")

            for i in range(min(10, guild_count)):
                guild_embed.add_field(name=joined_guilds[i][1], value=f"Joined on {joined_guilds[i][0]}. {joined_guilds[i][2]} members.", inline=False)
            
            guild_embed.set_footer(text=f"{config.bot_name} is in {guild_count} servers.")
            await inter.send(embed=guild_embed, ephemeral=True)

        
        else:
        #show all the guild info in one big message. 2,000 character limit
          
            guild_message = f"**__{config.bot_name} is in {guild_count} servers__** \n\n"
            for guild in joined_guilds:
                guild_message += f"__{guild[1]}__ \n"
                guild_message += f"*Joined on {guild[0]}. {guild[2]} members.* \n\n"
            
            
            try:
                await inter.send(guild_message, ephemeral=True)

            
            except disnake.HTTPException as e:
                if e.code == 50035:
                    #the message we tried to send was more than 2000 characters, so blocked by the API.
                    logging.warning(f"{config.bot_name} is in {guild_count} servers, message length was {len(guild_message)}")
                    await inter.send("I'm so popular, I'm in too many guilds to mention!")
                    

                else:
                    #some other HTTP exception
                    logging.exception(e)
                    await inter.send("Something went wrong, sorry!")
                    
            
            except Exception as e:
                #some other exception
                logging.exception(e)
                await inter.send("Something went wrong, sorry!")
                
          

    else:
        #user was not allowed to use this command.
        logging.info(f"{inter.author} tried to use the server_info command but was not authorised.")
        inter.send("That's not a command, it's a space station.", ephemeral=True)
        return




#----------------------------------------BOT RUN----------------------------------------#
if __name__ == "__main__":
    setup_logging()
    setup_db()
    bot.run(tokens.cfb_live_token)
