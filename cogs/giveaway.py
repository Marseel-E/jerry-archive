import discord, asyncio, random, humanize
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from backend.database import *
from backend.tools import *
from typing import Optional

GIVE = Command('giveaway')
END = Command('end')
EDIT = Command('edit')
REROLL = Command('reroll')


class Giveaway_view(discord.ui.View):
    def __init__(self, giveaway_id):
        super().__init__()
        self.giveaway_id = giveaway_id

    @discord.ui.button(label="Join (0)", style=discord.ButtonStyle.green)
    async def join(self, button : discord.ui.Button, interaction : discord.Interaction):
        guild = Guild(interaction.guild)
        try: giveaway = guild.data[f'giveaways'][self.giveaway_id]
        except KeyError:
            button.style = discord.ButtonStyle.gray
            button.disabled = True
            self.stop()
        
        try: required_roles = giveaway['roles_required']
        except KeyError: required_roles = None
        else:
            if required_roles != None:
                for role in required_roles:
                    user_roles = [str(user_role.id) for user_role in interaction.user.roles]
                    
                    if str(role) not in user_roles:
                        await interaction.response.send_message("You don't have all the requirements.", ephemeral=True)
                        return

        if button.label == "Join (0)":
                guild.update(f'giveaways/{self.giveaway_id}/entries', [interaction.user.id])
                button.label = f"Join  ({len(giveaway['entries'])})"

                await interaction.response.edit_message(view=self) 
                return

        if interaction.user.id in list(giveaway['entries']):
            await interaction.response.send_message("You've already joined.", ephemeral=True)
            return

        if "max_entries" in list(giveaway.keys()) and len(giveaway['entries'])+1 >= int(giveaway['max_entries']):
            guild.update(f'giveaways/{self.giveaway_id}/entries/{len(giveaway["entries"])}', interaction.user.id)

            button.label = f"{len(giveaway['entries'])+1}"
            button.style = discord.ButtonStyle.gray
            button.disabled = True
            
            self.stop()

        else:
            guild.update(f'giveaways/{self.giveaway_id}/entries/{len(giveaway["entries"])}', interaction.user.id)
            button.label = f"Join  ({len(giveaway['entries'])+1})"

        await interaction.response.edit_message(view=self)    

class Giveaway(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.giveaways_handler.start()
        
    def cog_unload(self): self.giveaways_handler.cancel()
    
    
    @tasks.loop(seconds=1.0)
    async def giveaways_handler(self):
        for guild_id, data in Database().data['guilds'].items():
            try: data['giveaways']
            except KeyError: continue
            
            for _id, giveaway in data['giveaways'].items():
                if 'start_time' in list(giveaway.keys()) and datetime.utcnow() >= Convert(giveaway['start_time']).datetime + timedelta(seconds=int(giveaway['time'])):
                    winners = random.choices(giveaway['entries'], k = int(giveaway['winners']))

                    channel = await self.bot.fetch_channel(giveaway['channel'])
                    message = await channel.fetch_message(giveaway['message'])
                    author = await self.bot.fetch_user(giveaway['author'])

                    description = ":crown: Winner(s): "
                    for winner in winners:
                        user = await self.bot.fetch_user(int(winner))
                        description += f"{user.mention}, "

                    embed = discord.Embed(title = giveaway['prize'], description = description, color = int(Static().color_green, 16))
                    embed.set_footer(text=f"By: {author} | " + Static().footer, icon_url=author.avatar.url)

                    view = Giveaway_view(_id)
                    view.join.disabled = True
                    view.join.label = len(giveaway['entries'])
                    view.style = discord.ButtonStyle.gray

                    await message.edit(content=":tada: Giveaway finished! :tada:", embed=embed, view=view)
                    view.stop()

                    Database().base.child('guilds').child(str(channel.guild.id)).child('giveaways').child(str(_id)).child('start_time').remove()

                    guild = await self.bot.fetch_guild(int(guild_id))
                    guild = Guild(guild)

                    guild.update(f'giveaways/{_id}/finished', True)
                    guild.update(f'giveaways/{_id}/expires_at', str(datetime.utcnow() + timedelta(hours=1)))

                if 'finished' in list(giveaway.keys()) and giveaway['finished'] == True:
                    if datetime.utcnow() >= Convert(giveaway['expires_at']).datetime:
                        Database().base.child('guilds').child(str(channel.guild.id)).child('giveaways').child(str(_id)).remove()
            
    @giveaways_handler.before_loop
    async def before_giveaways_handler(self):
        await self.bot.wait_until_ready()

    @commands.command(help=GIVE.help, aliases=GIVE.aliases)
    async def giveaway(self, ctx, **args : Optional[dict]):
        try: await ctx.message.delete()
        except: pass

        guild = Guild(ctx.guild)

        required_args = ['winners', 'time', 'prize', 'max_entries', 'text', 'roles_required', 'sponsor']
        requirements = ""

        if list(args.keys()) != required_args:
            def check(m):
                return m.guild.id == ctx.guild.id and m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            for arg in required_args:
                try: (args[arg])
                except KeyError: pass
                else: continue

                description = ""

                if arg == "sponsor": description += "\nResponse format: [sponsor (server) name](sponsor (server) invite link)\n"

                if arg in ['roles_required', 'max_entries', 'text', 'sponsor']:
                    description += f"```Note: respond with `no` if you dont want {arg.capitalize()}```"

                embed = discord.Embed(title=f"{arg.capitalize()}?", description=description, color=int(Static().color_default, 16))
                embed.set_footer(text=Static().footer, icon_url=ctx.author.avatar.url)
                
                msg = await ctx.send(embed=embed)

                try: message = await self.bot.wait_for('message', check=check, timeout=60)
                except asyncio.TimeoutError: await msg.delete(); await ctx.send("Request timed-out", delete_after=5); return
                else:
                    await msg.delete()

                    if arg in ["winners", "time"]:
                        if not message.content.isnumeric() or int(message.content) <= 0:
                            await ctx.send(f"Invalid value for `{arg}`", delete_after=15); return

                    if arg in ['max_entries', 'text', 'roles_required', 'sponsor']:
                        if message.content.lower() == "no": continue

                        else:
                            if arg == "max_entries":
                                if not message.content.isnumeric() or int(message.content) <= 1:
                                    await ctx.send(f"Max entries must be more than 2.", delete_after=15); return

                            if arg == "roles_required":
                                if len(message.role_mentions) < 1:
                                    await ctx.send(f"Couldn't read roles.", delete_after=15); return

                                roles_required = []
                                for role in message.role_mentions:
                                    roles_required.append(str(role.id))
                                    
                                    requirements += f"{role.mention} "

                                args[arg] = roles_required

                                await message.delete()
                                continue

                    args[arg] = message.content

                    await message.delete()

        args['start_time'] = str(datetime.utcnow())
        args['entries'] = [str(self.bot.user.id)]
        args['author'] = ctx.author.id
        args['channel'] = ctx.channel.id

        giveaway_id = str(Generate().id(16))

        guild.update(f"giveaways/{giveaway_id}", args)

        description = ""
        if 'text' in list(args.keys()): description += args['text'] + '\n'

        description += f"> :crown: - {args['winners']} ||`(winners)`||\n> :hourglass: - {humanize.precisedelta(timedelta(seconds=int(args['time'])))} ||`(time)`||\n"

        if "max_entries" in list(args.keys()):
            description += f"> :warning: - {args['max_entries']} ||`(max entries)`||\n"

        if 'sponsor' in list(args.keys()): description += f"Sponsored by **{args['sponsor']}**"
        
        embed = discord.Embed(title = args['prize'], description = description, color = int(Static().color_default, 16))
        embed.set_footer(text = f"By: {ctx.author} | " + Static().footer, icon_url = ctx.author.avatar.url)

        if requirements != "":
            embed.add_field(name = ":white_check_mark: Requirements:", value = requirements, inline = False)

        view = Giveaway_view(giveaway_id)

        msg = await ctx.send(content=":tada: Giveaway :tada:", embed=embed, view=view)
        
        guild.update(f"giveaways/{giveaway_id}/message", msg.id)

        await view.wait()

    @commands.command(help=END.help, aliases=END.aliases)
    async def end(self, ctx, target_id : Optional[int] = None):
        try: await ctx.message.delete()
        except: pass

        if target_id == None:
            msg = await ctx.send("What giveaway would you like to end?\n```\nNote: Respond with the message id of the target giveaway\n```")

            def check(m):
                return m.guild.id == ctx.guild.id and m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try: message = await self.bot.wait_for('message', check=check, timeout=120)
            except asyncio.TimeoutError:
                await msg.delete()
                await ctx.send("Request timed-out", delete_after=5)
                return
            else:
                await msg.delete()

                if not message.content.isnumeric():
                    await ctx.send(f"Couldn't find the message for '{message.content.lower()}'", delete_after=15)
                    return

                target_id = int(message.content)

        guilds = Database().data['guilds']

        msg = await ctx.send(f"Searching for giveaway...\nEstimated time: {humanize.precisedelta(timedelta(seconds=len(guilds)+5))}")

        for guild_id, guild in guilds.items():
            for giveaway_id, giveaway in guild['giveaways'].items():
                if int(giveaway['message']) == target_id:
                    await msg.delete()
                    await ctx.send("Giveaway found!", delete_after=3)

                    winners = random.choices(giveaway['entries'], k = int(giveaway['winners']))

                    channel = await self.bot.fetch_channel(giveaway['channel'])
                    message = await channel.fetch_message(giveaway['message'])
                    author = await self.bot.fetch_user(giveaway['author'])

                    description = ":crown: Winner(s): "
                    for winner in winners:
                        user = await self.bot.fetch_user(int(winner))
                        description += f"{user.mention}, "

                    embed = discord.Embed(title = giveaway['prize'], description = description, color = int(Static().color_green, 16))
                    embed.set_footer(text=f"By: {author} | " + Static().footer, icon_url=author.avatar.url)

                    await message.edit(content=":tada: Giveaway finished! :tada:", embed=embed)

                    Database().base.child('guilds').child(str(guild_id)).child('giveaways').child(str(giveaway_id)).remove()

        await ctx.send("Giveaway ended.", delete_after=5)

    @commands.command(help=EDIT.help, aliases=EDIT.aliases)
    async def edit(self, ctx, target_id : Optional[int] = None):
        try: await ctx.message.delete()
        except: pass

        if target_id == None:
            msg = await ctx.send("What giveaway would you like to edit?\n```\nNote: Respond with the message id of the target giveaway\n```")

            def check(m):
                return m.guild.id == ctx.guild.id and m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try: message = await self.bot.wait_for('message', check=check, timeout=120)
            except asyncio.TimeoutError:
                await msg.delete()
                await ctx.send("Request timed-out", delete_after=5)
                return
            else:
                await msg.delete()

                if not message.content.isnumeric():
                    await ctx.send(f"Couldn't find the message for '{message.content.lower()}'", delete_after=15)
                    return

                target_id = int(message.content)

        guilds = Database().data['guilds']

        msg = await ctx.send(f"Searching for giveaway...\nEstimated time: {humanize.precisedelta(timedelta(seconds=len(guilds)+5))}")

        for guild_id, guild in guilds.items():
            for giveaway_id, giveaway in guild['giveaways'].items():
                if int(giveaway['message']) == target_id:
                    await msg.delete()
                    await ctx.send("Giveaway found!", delete_after=3)

                    guild = await self.bot.fetch_guild(int(guild_id))
                    guild = Guild(guild)
                    
                    giveaway_id = giveaway_id
                    giveaway = giveaway

        editables = list(giveaway.keys())
        for no in ['message', 'channel', 'entries', 'author', 'start_time']: 
            editables.remove(no)

        msg = await ctx.send(f"What would you like to edit?\n`{', '.join(editables)}`")

        def check(m):
            return m.guild.id == ctx.guild.id and m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

        try: message = await self.bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await msg.delete()
            await ctx.send("Request timed-out", delete_after=5)
            return
        else:
            await msg.delete()

            if message.content.strip().lower() not in editables:
                await ctx.send(f"No such thing as '{message.content.strip().lower()}'", delete_after=15)
                return

            edit = message.content.strip().lower()
        
        msg = await ctx.send(f"{edit.capitalize()} ?")

        try: message = await self.bot.wait_for('message', check=check, timeout=60)
        except asyncio.TimeoutError:
            await msg.delete()
            await ctx.send("Request timed-out", delete_after=5)
            return
        else:
            await msg.delete()

            # max_entries, time, winners
            if edit in ['max_entries', 'time', 'winners']:
                if not message.content.isnumeric():
                    await ctx.send(f"Can't assign '{message.content.strip().lower()}' to `{edit}`", delete_after=15)
                    return

                if edit == 'max_entries' and int(message.content) < 2:
                    await ctx.send(f"Can't have less than 2 entries.", delete_after=15)
                    return

                if int(message.content) < 1:
                    await ctx.send(f"Can't have a zero or negative value.", delete_after=15)
                    return

                if edit == 'time':
                    guild.update(f'giveaways/{giveaway_id}/start_time', str(datetime.utcnow()))

                guild.update(f'giveaways/{giveaway_id}/{edit}', int(message.content))

            # prize, sponsor, text
            if edit in ['prize', 'sponsor', 'text']:
                guild.update(f'giveaways/{giveaway_id}/{edit}', message.content)

            # roles_required
            if edit == 'roles_required':
                if len(message.role_mentions) < 1:
                    await ctx.send(f"Couldn't read roles.", delete_after=15)
                    return

                roles_required = []
                message.content = ""
                for role in message.role_mentions:
                    roles_required.append(str(role.id))
                    
                    message.content += f"{role.mention} "

                guild.update(f'giveaways/{giveaway_id}/roles_required', roles_required)

        await ctx.send(f"Updated `{edit}` to `{message.content}`!", delete_after=15)

        channel = await self.bot.fetch_channel(int(giveaway['channel']))
        msg = await channel.fetch_message(target_id)
        author = await self.bot.fetch_user(giveaway['author'])
        giveaway = Guild(guild.discord).get('giveaways')[str(giveaway_id)]

        msg.embeds[0].clear_fields()

        description = ""
        if 'text' in list(giveaway.keys()): description += giveaway['text'] + '\n'

        description += f"> :crown: - {giveaway['winners']} ||`(winners)`||\n> :hourglass: - {humanize.precisedelta(timedelta(seconds=int(giveaway['time'])))} ||`(time)`||\n"

        if "max_entries" in list(giveaway.keys()):
            description += f"> :warning: - {giveaway['max_entries']} ||`(max entries)`||\n"

        if 'sponsor' in list(giveaway.keys()): description += f"Sponsored by **{giveaway['sponsor']}**"
        
        embed = discord.Embed(title = giveaway['prize'], description = description, color = int(Static().color_default, 16))
        embed.set_footer(text = f"By: {author} | " + Static().footer, icon_url = author.avatar.url)

        if 'roles_required' in list(giveaway.keys()):
            requirements = ""
            
            for role_id in giveaway['roles_required']:
                role = guild.discord.get_role(int(role_id))
                requirements += role.mention + ' '

            embed.add_field(name = ":white_check_mark: Requirements:", value = requirements, inline = False)

        await msg.edit(content=":tada: Giveaway :tada:", embed=embed)

    @commands.command(help=REROLL.help, aliases=REROLL.aliases)
    async def reroll(self, ctx, target_id : Optional[int] = None):
        try: await ctx.message.delete()
        except: pass

        if target_id == None:
            msg = await ctx.send("What giveaway would you like to reroll?\n```\nNote: Respond with the message id of the target giveaway\n```")

            def check(m):
                return m.guild.id == ctx.guild.id and m.channel.id == ctx.channel.id and m.author.id == ctx.author.id

            try: message = await self.bot.wait_for('message', check=check, timeout=120)
            except asyncio.TimeoutError:
                await msg.delete()
                await ctx.send("Request timed-out", delete_after=5)
                return
            else:
                await msg.delete()

                if not message.content.isnumeric():
                    await ctx.send(f"Couldn't find the message for '{message.content.lower()}'", delete_after=15)
                    return

                target_id = int(message.content)

        guilds = Database().data['guilds']

        msg = await ctx.send(f"Searching for giveaway...\nEstimated time: {humanize.precisedelta(timedelta(seconds=len(guilds)+5))}")

        for guild_id, guild in guilds.items():
            for giveaway_id, giveaway in guild['giveaways'].items():
                if int(giveaway['message']) == target_id:
                    await msg.delete()
                    await ctx.send("Giveaway found!", delete_after=3)

                    guild = await self.bot.fetch_guild(int(guild_id))
                    guild = Guild(guild)
                    
                    giveaway_id = giveaway_id
                    giveaway = giveaway

        if 'finished' not in list(giveaway.keys()) or giveaway['finished'] == False:
            await ctx.send("This giveaway is not finished yet.", delete_after=15)
            return

        winners = random.choices(giveaway['entries'], k = int(giveaway['winners']))

        channel = await self.bot.fetch_channel(giveaway['channel'])
        message = await channel.fetch_message(giveaway['message'])
        author = await self.bot.fetch_user(giveaway['author'])

        description = ":crown: Winner(s): "
        for winner in winners:
            user = await self.bot.fetch_user(int(winner))
            description += f"{user.mention}, "

        embed = discord.Embed(title = giveaway['prize'], description = description, color = int(Static().color_green, 16))
        embed.set_footer(text=f"By: {author} | " + Static().footer, icon_url=author.avatar.url)

        await message.edit(content=":tada: Giveaway finished! :tada:", embed=embed)

        guild.update(f'giveaways/{giveaway_id}/expires_at', str(datetime.utcnow() + timedelta(hours=1)))


def setup(bot):
    bot.add_cog(Giveaway(bot))