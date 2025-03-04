import os
import re
import json
import discord
from math import floor
from dotenv import load_dotenv
from discord.ext import commands

load_dotenv()

token = os.getenv("DISCORD_TOKEN")
bot_owner_id = int(os.getenv("BOT_OWNER_ID"))
guild_id = int(os.getenv("BOT_GUILD_ID"))
log_channel_id = int(os.getenv("MOD_LOG_CHANNEL"))

intents = discord.Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix="$", intents=intents)

def load_log():
	try:
		with open("main.json", "r") as file:
			if os.stat("main.json").st_size == 0:
				main = {}
			else:
				main = json.load(file)
			if "sniplog" not in main:
				main["sniplog"] = {}
			return main["sniplog"]
	except FileNotFoundError:
		return {}

def save_log(log):
	try:
		with open("main.json", "r") as file:
			main = json.load(file)
	except FileNotFoundError:
		main = {}

	if "sniplog" not in main:
		main["sniplog"] = {}
	main["sniplog"] = log

	with open("main.json", "w") as file:
		json.dump(main, file, indent=4)	

def get_xp(user_id):
	try:
		with open("main.json", "r") as file:
			if os.stat("main.json").st_size == 0:
				main = {}
			else:
				main = json.load(file)
			xp_log = main["xp"]
			if not user_id in xp_log:
				return 0
			return xp_log[user_id]
	except FileNotFoundError:
		return 0

def add_xp(user_id):
	try:
		with open("main.json", "r") as file:
			if os.stat("main.json").st_size == 0:
				main = {}
			else:
				main = json.load(file)
			
			if not "xp" in main:
				main["xp"] = {}
			xp_log = main["xp"]
	except FileNotFoundError:
		xp_log = {}

	xp_log.setdefault(user_id, 0)
	xp_log[user_id] += 1

	with open("main.json", "w+") as file:
		main["xp"] = xp_log
		file.seek(0)
		json.dump(main, file, indent=4)
		file.truncate()

	if xp_log[user_id] % 100 == 0:
		return xp_log[user_id] / 100
	else:
		return 0

def get_case():
	try:
		with open("main.json", "r") as file:
			main = json.load(file)
	except FileNotFoundError:
		main = {}

	main.setdefault("case", 0)
	main["case"] += 1
	case = main["case"]

	with open("main.json", "w") as file:
		json.dump(main, file, indent=4)

	return case

# Error

@client.tree.error
async def on_error(interaction, error):
	embed = discord.Embed(title="Severe Error", description=error)
	await interaction.response.send_message(embed=embed, ephemeral=True)

# Startup

@client.event
async def on_ready():
	print(f"Logged in as {client.user}!")
	await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="outside your window."))

# User message handling (XP)

@client.event
async def on_message(message):
	if message.author.bot:
		return
	user_id = message.author.id
	xp = int(add_xp(str(user_id)))
	if xp > 0:
		embed = discord.Embed(title="Level up!", description=f"You reached level **{xp}**!")
		embed.set_author(name=f"{message.author.name}", icon_url=f"{message.author.avatar.url}")
		await message.channel.send(embed=embed)

# XP

async def xp(member: discord.Member):
	cur_xp = get_xp(str(member.id))
	level = int(floor(cur_xp / 100) + 1)
	rem_xp = ((level + 1) * 100) - (cur_xp + 100)
	embed = discord.Embed(title="Level", description=f"**Level {level}** @ `{cur_xp} XP`")
	embed.set_author(name=f"{member.name}", icon_url=f"{member.avatar.url}")
	embed.set_footer(text=f"{rem_xp} XP left to level {level + 1}.")
	return embed
@client.command(name="xp", description="View your current XP and level.")
async def xp_prefixed(ctx):
	await ctx.send(embed=await xp(ctx.author), delete_after=8)
@client.tree.command(name="xp", description="View your current XP and level.", guild=discord.Object(id=guild_id))
async def xp_interaction(interaction):
	await interaction.response.send_message(embed=await xp(interaction.user), ephemeral=True)

# Sync

async def sync(user_id: int):
	if not user_id == bot_owner_id:
		return "Invalid permission."
	cmds = await client.tree.sync(guild=discord.Object(id=guild_id))
	return f"Synced {len(cmds)} commands."	
@client.command(name="sync", description="Sync commands to guild.")
async def sync_prefixed(ctx):
	await ctx.send(await sync(ctx.author.id), delete_after=8)
@client.tree.command(name="sync", description="Sync commands to guild.", guild=discord.Object(id=guild_id))
async def sync_interaction(interaction):
	await interaction.response.send_message(await sync(interaction.user.id), ephemeral=True)

# Ping

async def ping():
	latency = round(client.latency * 1000)
	return discord.Embed(title="Pong!", description=f"Took {latency}ms.")
@client.command(name="ping", description="Ping. Pong.")
async def ping_prefix(ctx):
	await ctx.send(embed=await ping(), delete_after=5)
@client.tree.command(name="ping", description="Ping. Pong.", guild=discord.Object(id=guild_id))
async def ping_interaction(interaction):
	await interaction.response.send_message(embed=await ping(), ephemeral=True)


# Say

@client.tree.command(name="say", description="Bot say beep boop", guild=discord.Object(id=guild_id))
async def say(interaction, text: str, reply: str = None):
	# Advised you don't give anyone say permissions, although making it admin is appropriate for some servers.
	if not interaction.user.id == bot_owner_id:
		await interaction.response.send_message("Nope.", ephemeral=True)
		return
	if reply == None:
		await interaction.channel.send(text)
		await interaction.response.send_message("Sent!", ephemeral=True)
	else:
		channel = interaction.channel
		message = await channel.fetch_message(int(reply))

		await message.reply(text)
		await interaction.response.send_message("Sent!", ephemeral=True)

#
# Snip functions
#

# Snip

async def snip(name: str):
	snipname = "snips/" + name + ".txt"
	try:
		file = open(snipname, 'r')
	except FileNotFoundError:
		return discord.Embed(title="Error", description=f"Snip {name} doesn't exist.")
	else:
		with file:
			content = file.read()	
			return discord.Embed(title=f"{snipname}", description=f"\"{content}\"")
@client.command(name="snip", description="View a snip.")
async def sync_prefixed(ctx, name: str):
	await ctx.send(embed=await snip(name))
@client.tree.command(name="snip", description="View a snip.", guild=discord.Object(id=guild_id))
async def snip_interaction(interaction, name: str):
	await interaction.response.send_message(embed=await snip(name))

# Create

async def create(name: str, content: str, user_id: int):
	path = "snips/" + name + ".txt"
	if not os.path.isdir("snips"):
		os.mkdir("snips")
	if os.path.exists(path):
		return discord.Embed(title="Error", description=f"Snip `{name}` already exists.")
	else:
		with open(path, 'w') as file:
			file.write(content)
		log = load_log()
		log[name] = user_id
		save_log(log)
		return discord.Embed(title="Success", description="Created snip.")
@client.command(name="create", description="Create a snip.")
async def create_prefixed(ctx, name: str, *args):
	content = " ".join(args)
	await ctx.send(embed=await create(name, content, ctx.author.id), delete_after=8)		
@client.tree.command(name="create", description="Create a snip.", guild=discord.Object(id=guild_id))
async def create_interaction(interaction, name: str, content: str):
	await interaction.response.send_message(embed=await create(name, content, interaction.user.id), ephemeral=True)

# whois

async def whois(name: str):
	fullname = "snips/" + name + ".txt"
	log = load_log()
	owner_id = log[name]
	user = await client.fetch_user(int(owner_id))
	username = user.name
	return discord.Embed(title="Info", description=f"Snip `{name}` belongs to {username}.")
@client.command(name="whois", description="Find who owns a snip.")
async def whois_prefix(ctx, name: str):
	await ctx.send(embed=await whois(name), delete_after=8)
@client.tree.command(name="whois", description="Find who owns a snip.", guild=discord.Object(id=guild_id))
async def whois_interaction(interaction, name: str):
	await interaction.response.send_message(embed=await whois(name), ephemeral=True)

# Delete

async def delete(name: str, user_id: int):
	path = "snips/" + name + ".txt"
	log = load_log()
	if log[name] != user_id and not message.author.guild_permissions.manage_messages:
		return discord.Embed(title="Error", description="Invalid permission.")
	if name in log:
		del log[name]
	save_log(log)
	try:
		os.remove(path)
	except FileNotFoundError:
		return discord.Embed(title="Success, but Error.", description="Deleted from record, but missing from disk.")
	else:
		return discord.Embed(title="Success", description="Deleted.")
@client.command(name="delete", description="Delete a snip.")
async def delete_prefix(ctx, name: str):
	await ctx.send(embed=await delete(name, ctx.author.id), delete_after=8)
@client.tree.command(name="delete", description="Delete a snip.", guild=discord.Object(id=guild_id))
async def delete_interaction(interaction, name: str):
	await interaction.response.send_message(embed=await delete(name, interaction.user.id), ephemeral=True)

# List

async def list(usingprefix: bool):
	log = load_log()
	format_log = []
	for key, value in log.items():
		try:
			user = await client.fetch_user(int(value))
			username = user.name
		except discord.NotFound:
			username = "Unknown"
		except discord.HTTPException:
			username = "Unknown"
		format_log.append(f"`{key}` - {username}")
	string = "\n".join(format_log)
	if not string:
		return discord.Embed(title="Minor issue...", description="No snips.")
	else:
		embed = discord.Embed(title="Saved Snips", description=string)
		if usingprefix:
			embed.set_footer(text="To view the list for longer, use the slash command.")
		return embed
@client.command(name="list", description="List all snips.")
async def list_prefix(ctx):
	await ctx.send(embed=await list(True), delete_after=8)
@client.tree.command(name="list", description="List all snips.", guild=discord.Object(id=guild_id))
async def list_interaction(interaction):
	await interaction.response.send_message(embed=await list(False), ephemeral=True)

#
# Moderation (scary)
#

# Ban

async def ban(caller: discord.Member, member: discord.Member, reason: str):
	if not caller.guild_permissions.ban_members:
		return "Insufficient permission to ban members."
	try:
		case = get_case()

		channel = client.get_channel(log_channel_id)
		embed = discord.Embed(title=f"case no. {str(case)}", color=0xeb4034)
		embed.set_thumbnail(url=member.avatar.url)
		embed.add_field(name="Action: Ban", value=f"Reason: `{reason}`", inline=False)
		embed.add_field(name="Moderator:", value=f"`{caller.name}` - {caller.mention}", inline=True)
		embed.add_field(name="Target:", value=f"`{member.name}` - {member.mention}", inline=True)
		await channel.send(embed=embed)

		await member.ban(reason=reason)
		return f"Banned **{member.name}**."
	except discord.Forbidden:
		return "Bot does not have ban members permission."
@client.command(name="ban", description="Ban a member from the server.")
async def ban_prefix(ctx, member: discord.Member, *args):
	reason = " ".join(args)
	await ctx.send(await ban(ctx.author, member, reason))
@client.tree.command(name="ban", description="Ban a member from the server.", guild=discord.Object(id=guild_id))
async def ban_interaction(interaction, member: discord.Member, reason: str):
	await interaction.response.send_message(await ban(interaction.user, member, reason), ephemeral=True)

# Unban

@client.command(name="unban", description="Unban a member from the server.")
async def unban_prefix(ctx, member: int):
	if not ctx.author.guild_permissions.ban_members:
		await ctx.send("Insufficient permission to ban members.", delete_after=8)
		return
	user = await client.fetch_user(member)
	try:
		await ctx.guild.unban(user)
		await ctx.send(f"Unbanned **{user.name}**.", delete_after=8)
	except discord.NotFound:
		await ctx.send(f"**{user.name}** isn't banned.", delete_after=8)
	except discord.Forbidden:
		await ctx.send("Insufficient permission for bot to ban member.", delete_after=8)
@client.tree.command(name="unban", description="Unban a member from the server.", guild=discord.Object(id=guild_id))
async def unban_interaction(interaction, member: str):
	if not interaction.user.guild_permissions.ban_members:
		interaction.response.send_message("Insufficient permission to ban members.", ephemeral=True)
		return
	try:
		member_int = int(member)
	except ValueError:
		await interaction.response.send_message("Invalid User ID.", ephemeral=True)
		return
	user = await client.fetch_user(member_int)
	try:
		await interaction.guild.unban(user)
		await interaction.response.send_message(f"Unbanned {user.name}.", ephemeral=True)
	except discord.NotFound:
		await interaction.response.send_message(f"{user.name} isn't banned.", ephemeral=True)
	except discord.Forbidden:
		await interaction.response.send_message("Insufficient permission for bot to ban member.", ephemeral=True)

# Kick

async def kick(caller: discord.Member, member: discord.Member, reason: str):
	if not caller.guild_permissions.kick_members:
		return "Insufficient permissions to kick members."
	try:
		await member.kick()

		case = get_case()

		channel = client.get_channel(log_channel_id)
		embed = discord.Embed(title=f"case no. {str(case)}", color=0xfcba03)
		embed.set_thumbnail(url=member.avatar.url)
		embed.add_field(name="Action: Kick", value=f"Reason: `{reason}`", inline=False)
		embed.add_field(name="Moderator:", value=f"`{caller.name}` - {caller.mention}", inline=True)
		embed.add_field(name="Target:", value=f"`{member.name}` - {member.mention}", inline=True)
		await channel.send(embed=embed)

		return f"Kicked **{member.name}**."
	except discord.Forbidden:
		return "Insufficient permission for bot to kick member."
@client.command(name="kick", description="Kick a member from the server.")
async def kick_prefix(ctx, member: discord.Member, *args):
	reason = " ".join(args)
	await ctx.send(await kick(ctx.author, member, reason), delete_after=8)
@client.tree.command(name="kick", description="Kick a member from the server.", guild=discord.Object(id=guild_id))
async def kick_interaction(interaction, member: discord.Member, reason: str):
	await interaction.response.send_message(await kick(interaction.user, member, reason), ephemeral=True)

client.run(token)