#!/usr/bin/env python3
from typing import Optional, List, Tuple, Callable, Dict, Union
import discord
from bs4 import BeautifulSoup as BS
from discord.ext import commands
import PIL.Image
import PIL.ImageOps
import PIL.ImageFilter
import PIL.ImageEnhance
import io
import asyncio
import urllib.request
import random
from .errorwithmessage import ErrorWithMessage
import subprocess

bot = commands.Bot(command_prefix=">", activity=discord.Game("use >jpeg"))

def is_owner(ctx) -> bool:
	return bot.is_owner(ctx.message.author)


@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, discord.ext.commands.CommandNotFound):
		return
	elif isinstance(error.__cause__, discord.errors.Forbidden):
		await ctx.message.add_reaction("⛔")
	elif isinstance(error.__cause__, PIL.Image.DecompressionBombError):
		await ctx.message.add_reaction("😵")
	elif isinstance(error.__cause__, ErrorWithMessage):
		await ctx.message.add_reaction("⚠")
		await ctx.send(error.__cause__.msg)
	else:
		await ctx.message.add_reaction("⚠")
		raise error
		
@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
	if payload.user_id == bot.user.id: # ignore our own reactions
		return
	if payload.emoji.name == "❌": # deletion request
		message = await bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
		if message.author != bot.user:
			return
		if (not payload.member.bot) and payload.member in message.mentions:
			await message.delete()
			await message.channel.send("Deleted", delete_after=5)
"""
@bot.event
async def on_reaction_add(reaction: discord.Reaction, user: Union[discord.Member, discord.User]):
	if reaction.message.author != bot.user or reaction.emoji != "❌":
		return
	async for user in reaction.users():
		if (not user.bot) and user in reaction.message.mentions:
			await reaction.message.delete()
			await reaction.message.channel.send("Deleted", delete_after=5)
	"""


@bot.command(hidden=True)
@commands.check(is_owner)
async def quit(ctx):
#	await ctx.send("Goodbye")
	await ctx.message.add_reaction("👋")
	await ctx.bot.logout()

@bot.command()
async def whoami(ctx):
	"Shows your nick, global name, and user id.\nFor when you're having an existential crisis."
	member = ctx.message.author
	if isinstance(member, discord.Member):
		await ctx.send("You are {0} on this server, {1} globally, and have id {2}. ".format(
				member.nick or member.name, member.name + "#" + member.discriminator, member.id)
		)
	else:
		await ctx.send("You are {0} globally, and have id {1}. ".format(
				member.name + "#" + member.discriminator, member.id)
		)

@bot.command()
async def goodbot(ctx):
	"🥺"
	await ctx.message.add_reaction("🥰")

@bot.command()
async def source(ctx):
	"Links to the github source for this bot"
	branch = subprocess.Popen("git status".split(), stdout=subprocess.PIPE).communicate()[0].decode().split()[2]
	rev = subprocess.Popen("git rev-parse --short HEAD".split(), stdout=subprocess.PIPE).communicate()[0].decode().strip()
	await ctx.send("Source: https://github.com/zachs18/needsmorejpeg/ (running branch {}, rev {})".format(branch, rev))

@bot.command()
async def whois(ctx):
	"Shows the nick, global name, and user id of @mentioned users."
	mentions = ctx.message.mentions
	if mentions:
		await ctx.send('\n'.join("{0} is {0} on this server, {1} globally, and has id {2}.".format(
				member.nick or member.name, member.name + "#" + member.discriminator, member.id)
				for member in mentions)
		)
	else:
		await ctx.message.add_reaction("⚠")
		await ctx.send("Who is ... who?")

@bot.command()
@commands.check(is_owner)
async def addvoice(ctx):
	bot.load_extension("needsmorejpeg.cogs.voicecog")
	await ctx.message.add_reaction("✅")

@bot.command()
@commands.check(is_owner)
async def removevoice(ctx):
	bot.unload_extension("needsmorejpeg.cogs.voicecog")
	await ctx.message.add_reaction("✅")

@bot.command()
@commands.check(is_owner)
async def reloadvoice(ctx):
	bot.reload_extension("needsmorejpeg.cogs.voicecog")
	await ctx.message.add_reaction("✅")

bot.load_extension("needsmorejpeg.cogs.voicecog")
