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
	else:
		await ctx.message.add_reaction("⚠")
		raise error

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
	await ctx.send("Source: https://github.com/zachs18/needsmorejpeg/")

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
