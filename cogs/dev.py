import discord, sys, traceback, os, asyncio, json
from discord.ext import commands
from io import StringIO
from backend.database import *
from backend.tools import *
from typing import Optional, Union

def is_dev(ctx): return True if ctx.author.id in [470866478720090114, 652084886496346133] else False

PY = Command('py')
LOAD = Command('load')
RELOAD = Command('reload')
UNLOAD = Command('unload')

class Developer(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	@commands.command(help=PY.help, aliases=PY.aliases)
	@commands.is_owner()
	async def py(self, ctx, unformatted : Optional[bool], *, cmd):
		await ctx.message.delete()

		old_stdout = sys.stdout
		redirected_output = sys.stdout = StringIO()

		try:
			exec(str(cmd))
		except Exception as e:
			traceback.print_stack(file=sys.stdout)

			print(sys.exc_info())
		
		sys.stdout = old_stdout

		if (unformatted):
			msg = str(redirected_output.getvalue())
			msg = [await ctx.send(msg[i:i+2000]) for i in range(0, len(msg), 2000)]

		else:
			msg = str(redirected_output.getvalue())

			for i in range(0, len(msg), 2048):
				embed = discord.Embed(description=f"Input:\n{Style(cmd, 'py').box}\nOutput:\n{Style(msg[i:i+2000], 'r').box}", color=int(Static().color_invisible, 16))
				embed.set_footer(text=Static().footer)

				await ctx.send(embed=embed)


	@commands.command(help=LOAD.help)
	@commands.check(is_dev)
	async def load(self, ctx, cog : Optional[str]):
		if (cog):
			if cog.endswith(".py"):
				cog = cog[:-3]

			try: self.bot.load_extension(f"cogs.{cog}")
			except Exception as e: await ctx.author.send(f"\nFailed to load '{cog}':\n{e}\n")
			else: await ctx.send(f"'{cog}' Loaded..\n", delete_after=5)

		else:
			await ctx.message.add_reaction('✅')

			def check(reaction, user): return reaction.emoji == '✅' and ctx.author == user

			try: reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=15)
			except asyncio.TimeoutError: await ctx.message.delete()

			else:
				for file in os.listdir("cogs"):
					if file.endswith(".py"):
						if file[:-3] != "dev":
							try: self.bot.load_extension(f"cogs.{file[:-3]}")
							except Exception as e: await ctx.author.send(f"\nFailed to load '{file[:-3]}':\n{e}\n")
							else: await ctx.send(f"'{file[:-3]}' Loaded..\n", delete_after=5)

	@commands.command(help=RELOAD.help)
	@commands.check(is_dev)
	async def reload(self, ctx, cog : Optional[str]):
		if (cog):
			if cog.endswith(".py"): cog = cog[:-3]

			try: self.bot.reload_extension(f"cogs.{cog}")
			except Exception as e: await ctx.author.send(f"Failed to reload '{cog}':\n{e}\n")
			else: await ctx.send(f"'{cog}' Reloaded.\n", delete_after=5)

		else:
			await ctx.message.add_reaction('✅')

			def check(reaction, user): return reaction.emoji == '✅' and ctx.author == user

			try: reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=15)
			except asyncio.TimeoutError: await ctx.message.delete()

			else:
				for file in os.listdir("cogs"):
					if file.endswith(".py"):
						try: self.bot.reload_extension(f"cogs.{file[:-3]}")
						except Exception as e: await ctx.author.send(f"Failed to reload '{file[:-3]}':\n{e}\n")
						else: await ctx.send(f"'{file[:-3]}' Reloaded.\n", delete_after=5)

	@commands.command(help=UNLOAD.help)
	@commands.check(is_dev)
	async def unload(self, ctx, cog : Optional[str]):
		if (cog):
			if cog.endswith(".py"): cog = cog[:-3]
			if cog == "dev": return

			try: self.bot.unload_extension(f"cogs.{cog}")
			except Exception as e: await ctx.author.send(f"Failed to unload '{cog}':\n{e}\n")
			else: await ctx.send(f"'{cog}' Unloaded.\n", delete_after=5)
		else:
			await ctx.message.add_reaction('✅')

			def check(reaction, user): return reaction.emoji == '✅' and ctx.author == user

			try: reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout=15)
			except asyncio.TimeoutError: await ctx.message.delete()

			else:
				for file in os.listdir("cogs"):
					if file.endswith(".py"):
						if file[:-3] != "dev":
							try: self.bot.unload_extension(f"cogs.{file[:-3]}")
							except Exception as e: await ctx.author.send(f"Failed to reload '{file[:-3]}':\n{e}\n")
							else: await ctx.send(f"'{file[:-3]} Unloaded.\n'", delete_after=5)

	@commands.command(hidden=True)
	@commands.check(is_dev)
	@commands.has_permissions(manage_messages=True)
	async def purge(self, ctx, amount = 1):
		if amount >= 10:
			embed = discord.Embed(description=f"Are you sure you want to delete {Style(amount).highlight} messages?", color=int(Static().color_invisible, 16))            
			embed.set_footer(text=Static().footer)

			msg = await ctx.send(embed=embed)
			await msg.add_reaction('✅')

			def check(reaction, user): return reaction.emoji == '✅' and user == ctx.author

			try: reaction, user = await self.bot.wait_for('reaction_add', check=check, timeout = 15)
			except asyncio.TimeoutError:
				await ctx.message.delete()
				await msg.delete()

				return

			else:
				await msg.delete()
				pass

		await ctx.message.delete()
		await ctx.channel.purge(limit=int(amount))

		embed = discord.Embed(description=f"Deleted {Style(amount).highlight} messages in {Style(ctx.guild.name).highlight} ({Style(ctx.channel.name).highlight})", color=f"0x{Static().color_invisible}")
		embed.set_footer(text=Static().footer)
		await ctx.author.send(embed=embed, delete_after=30)


def setup(bot):
	bot.add_cog(Developer(bot))