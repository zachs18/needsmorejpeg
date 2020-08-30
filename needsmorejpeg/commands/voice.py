#!/usr/bin/env python3
from typing import Optional
import subprocess
import discord # import FFmpegAudio
import urllib
import io
import os
import tempfile
import asyncio

from ..bot import bot, commands, is_owner

@bot.command()
async def say(ctx, *, args: str, espeak_args = []):
	"Joins the voice channel you are in and says what you passed to it"
	try:
		voice_channel = ctx.author.voice.channel
		voice_channel.name # raise AttributeError if voice_channel is None
	except AttributeError:
		await ctx.send("Could not find a voice channel")
		raise ValueError

	stderr = tempfile.TemporaryFile()

	try:
		espeak = subprocess.Popen(["espeak", "--stdout", *espeak_args], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=stderr)
	except FileNotFoundError:
		await ctx.send("Could not open espeak to generate voice")
		raise ValueError

	espeak.stdin.write(args.encode())
	espeak.stdin.close()

	# voice_data_wave = espeak.stdout.read()
	voice_data = discord.FFmpegOpusAudio(espeak.stdout, pipe=True)

	if (espeak.poll() is not None and espeak.poll()):
		stderr.seek(0)
		await ctx.send("Error: %s" % stderr.read().decode())
		await ctx.message.add_reaction("🔇")
		return

	if ctx.message.guild.voice_client is not None and ctx.message.guild.voice_client.is_connected():
		voice_client = ctx.message.guild.voice_client
	else:
		voice_client = await voice_channel.connect()

	voice_client.play(voice_data)
	await ctx.message.add_reaction("✅")

@bot.command()
async def say_slow(ctx, *, args: str):
	await say(ctx, args=args, espeak_args = ["-s", "90"])

@bot.command()
async def say_fast(ctx, *, args: str):
	await say(ctx, args=args, espeak_args = ["-s", "200"])

@bot.command()
async def say_speed(ctx, speed: int, *, args: str):
	await say(ctx, args=args, espeak_args = ["-s", str(speed)])

@bot.command()
async def say_voice(ctx, voice: str, *, args: str):
	await say(ctx, args=args, espeak_args = ["-v", voice])

@bot.command()
async def leave(ctx):
	"Leaves the voice channel you are in"
	try:
		voice_channel = ctx.author.voice.channel
		voice_channel.name # raise AttributeError if voice_channel is None
	except AttributeError:
		await ctx.send("Could not find a voice channel")
		raise ValueError

	if ctx.message.guild.voice_client is not None and ctx.message.guild.voice_client.is_connected():
		voice_client = ctx.message.guild.voice_client
	else:
		await ctx.send("Could not find a voice channel")
		raise ValueError

	await voice_client.disconnect()
	await ctx.message.add_reaction("✅")

headers = {
	"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv76.0) Gecko/20100101 Firefox 76.0",
}

@bot.command()
#@commands.check(is_owner)
async def play(ctx, arg: Optional[str]):
	"Joins the voice channel you are in and plays what you passed to it"
	try:
		voice_channel = ctx.author.voice.channel
		voice_channel.name # raise AttributeError if voice_channel is None
	except AttributeError:
		await ctx.send("Could not find a voice channel")
		raise ValueError

	await ctx.message.add_reaction("🔜")

	if ctx.message.attachments:
		data = await ctx.message.attachments[0].read()
	else:
		request = urllib.request.Request(arg, None, headers=headers)
		response = urllib.request.urlopen(request)
		if not response:
			raise ValueError
		data = response.read()

	file = tempfile.TemporaryFile()
	file.write(data)
	file.seek(0)

	# voice_data_wave = espeak.stdout.read()
	voice_data = discord.FFmpegOpusAudio(file, pipe=True)

	if ctx.message.guild.voice_client is not None and ctx.message.guild.voice_client.is_connected():
		voice_client = ctx.message.guild.voice_client
	else:
		voice_client = await voice_channel.connect()

	voice_client.play(voice_data)
	await ctx.message.add_reaction("✅")

@bot.command()
async def yt(ctx, arg: str):
	"Joins the voice channel you are in and plays what you passed to it"
	try:
		voice_channel = ctx.author.voice.channel
		voice_channel.name # raise AttributeError if voice_channel is None
	except AttributeError:
		await ctx.send("Could not find a voice channel")
		raise ValueError

	if arg.startswith('-') or not (arg.startswith('http') or arg.startswith('ytsearch:')):
		await ctx.send("Invalid URL")
		raise ValueEroor

	fd, filename = tempfile.mkstemp(suffix=".mp3")

	await ctx.message.add_reaction("🔜")

	ytdl = subprocess.Popen(["youtube-dl", arg, "--no-playlist", "--no-continue", "-f", "bestaudio", "--extract-audio", "--audio-format", "mp3", "-o", filename])
	while ytdl.poll() is None:
		await asyncio.sleep(1)

	# voice_data_wave = espeak.stdout.read()
	voice_data = discord.FFmpegOpusAudio(filename, pipe=False)

	if ctx.message.guild.voice_client is not None and ctx.message.guild.voice_client.is_connected():
		voice_client = ctx.message.guild.voice_client
	else:
		voice_client = await voice_channel.connect()

	#os.remove(filename) # I don't know if ffmpeg is guaranteed to have opened the file yet, so remove it in a callback
	voice_client.play(voice_data, after = lambda: os.remove(filename))

	await ctx.message.add_reaction("✅")

