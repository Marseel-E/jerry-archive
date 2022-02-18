import discord, os
from discord.ext import commands
from dotenv import load_dotenv
from backend.database import *
from backend.tools import *


load_dotenv('.env')


intents = discord.Intents.all()
bot = commands.Bot(command_prefix=".", case_sensitive=True, intents=intents)


@bot.event
async def on_ready():
	print(bot.user.name + " has risen!")

	await bot.change_presence(status=discord.Status.online, activity=discord.Game(f"{Static().bot_name}.exe"))


@bot.event
async def on_message(message):
	if (message.author.bot):
		return

	if bot.user.mentioned_in(message):
		await message.channel.send(f"{message.author.mention}, Try '`.help`'")

		return
	
	await bot.process_commands(message)


class Help(commands.HelpCommand):
	def get_command_signature(self, command):
		if (command.signature):
			return f"{Style(self.context.clean_prefix).highlight}{Style(command.qualified_name).bold} {Style(command.signature).highlight}"
		
		return f"{Style(self.context.clean_prefix).highlight}{Style(command.qualified_name).bold}"

	async def send_bot_help(self, mapping):
		embed = discord.Embed(title=f"{Static().bot_name} - Help" , description="<> = Required\n[] = Optional" , color=int(Static().color_default, 16))
		embed.set_footer(text=Static().footer)
		
		for cog, commands in mapping.items():
			commands = await self.filter_commands(commands)
			command_signatures = [self.get_command_signature(c) for c in commands]
			
			if command_signatures:
				cog_name = getattr(cog, "qualified_name", "No category")
				embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

		channel = self.get_destination()
		
		await channel.send(embed=embed)

	async def send_cog_help(self, cog):
		desc = ""
		commands = await self.filter_commands(cog.get_commands())
		
		for cmd in commands:
			desc += f"{self.get_command_signature(cmd)}\n"
		
		embed = discord.Embed(title=f"Help - {cog.qualified_name}", description=f"() = Required\n[] = Optional\n\n{Style('Commands:').bold}\n{desc}", color=int(Static().color_default, 16))
		embed.set_footer(text=Static().footer)

		channel = self.get_destination()
		
		await channel.send(embed=embed)
	
	async def send_group_help(self, group):
		embed = discord.Embed(title=f"{group.cog_name} - {group.name}" , description=f"{self.get_command_signature(group)}" , color=int(Static().color_default, 16))
		embed.set_footer(text=Static().footer)
		
		embed.add_field(name="Description", value=group.help)
		
		if group.aliases:
			embed.add_field(name="Aliases", value=", ".join(group.aliases), inline=False)
		
		if group.commands:
			V = ""
			
			for cmd in group.commands:
				V += f"\n{cmd.qualified_name}".replace(f'{group.name} ', '')
				
				if (cmd.aliases):
					V += f" ({Style(', '.join(cmd.aliases)).highlight})"
			
			embed.add_field(name="Subcommands", value=V, inline=False)

		channel = self.get_destination()
		
		await channel.send(embed=embed)

	async def send_command_help(self, command):
		embed = discord.Embed(title=f"{command.cog_name} - {command.name}" , description=f"{self.get_command_signature(command)}" , color=int(Static().color_default, 16))
		embed.set_footer(text=Static().footer)
		
		embed.add_field(name="Description", value=command.help)
		
		alias = command.aliases
		
		if alias:
			embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

		channel = self.get_destination()
		
		await channel.send(embed=embed)

bot.help_command = Help()


if __name__ == ('__main__'):
	for file in os.listdir("cogs"):
		if file.endswith(".py"):
			try:
				bot.load_extension(f"cogs.{file[:-3]}")
			except Exception as e:
				print(f"\nFailed to load '{file[:-3]}':\n{e}\n")
			else:
				print(f"'{file[:-3]}' Loaded..\n")


bot.run(os.environ.get("TOKEN"))