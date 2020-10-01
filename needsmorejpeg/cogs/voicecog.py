#!/usr/bin/env python3
from typing import Optional, Dict, Callable
import subprocess
import discord # import FFmpegAudio
from discord.ext import commands
import urllib
import io
import os
import tempfile
import asyncio
from collections import namedtuple

from ..errorwithmessage import ErrorWithMessage

headers = {
	"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:76.0) Gecko/20100101 Firefox/76.0",
}

class QueueItem:
	def __init__(self, voice_data, ctx, description, callbacks=[]):
		self.voice_data = voice_data
		self.ctx = ctx
		self.description = description
		self.callbacks = callbacks

class VoiceCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.connections: Dict[discord.Guild, discord.VoiceClient] = dict()
		self.queues: Dict[discord.Guild, List[QueueItem]] = dict()

	def make_async_callback(self, *coros) -> Callable[[object], None]:
		def callback(error) -> None:
			for coro in coros:
				if isinstance(coro, type(lambda:None)): # This is a function, not a coroutine
					coro()
				else: # This is a coroutine
					asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
		return callback

	async def _get_voice_client(self, ctx, connect_if_not_connected = True) -> discord.VoiceClient:
		if (voice_client := ctx.guild.voice_client) is None or not voice_client.is_connected():
			if connect_if_not_connected:
				voice_client = self.connections[ctx.guild] = await ctx.author.voice.channel.connect()
			else:
				voice_client = None
		return voice_client

	async def _do_play(self, ctx, voice_data):
		voice_client = await self._get_voice_client(ctx)
#		voice_client.play(voice_data, after = lambda e: asyncio.run_coroutine_threadsafe(ctx.message.add_reaction("✅"), self.bot.loop))
		voice_client.play(voice_data, after = self.make_async_callback(ctx.message.add_reaction("✅")))

	async def _enqueue_item(self, ctx, voice_data, description: str, callbacks = []):
		voice_client = await self._get_voice_client(ctx)

		queue_item = QueueItem(voice_data, ctx, description)

		if ctx.guild not in self.queues:
			self.queues[ctx.guild] = [queue_item]
		else:
			self.queues[ctx.guild].append(queue_item)

		await self._play_next_if_not_playing(ctx)

	async def _play_next_if_not_playing(self, ctx):
		voice_client = await self._get_voice_client(ctx, False)
		if voice_client is not None and voice_client.is_playing():
			# Playing
			return
		if (queue := self.queues.get(ctx.guild, None)) is None or len(queue) == 0:
			# Not playing, Queue empty
			if voice_client is None:
				return
			await asyncio.sleep(3)
			if voice_client.is_connected() and not voice_client.is_playing():
				await voice_client.disconnect()
			return
		voice_client = await self._get_voice_client(ctx)
		queue_item = queue.pop(0)
		voice_client.play(queue_item.voice_data, after = self.make_async_callback(
			queue_item.ctx.message.add_reaction("✅"),
			self._play_next_if_not_playing(ctx),
			*queue_item.callbacks
		))

	@commands.command()
	async def skip(self, ctx):
		voice_client = await self._get_voice_client(ctx)
		voice_client.stop()

	@commands.command()
	async def queue(self, ctx):
		msg = None
		if ctx.guild in self.queues:
			msg = '\n'.join("{}: {}".format(i, item.description) for i,item in enumerate(self.queues[ctx.guild]))
		msg = msg or "No items in queue.")
		await ctx.send(msg)

	@commands.command()
	async def leave(self, ctx):
		voice_client = await self._get_voice_client(ctx, connect_if_not_connected=False)

		if voice_client is not None:
			await voice_client.disconnect()
			await ctx.message.add_reaction("✅")
		else:
			await ctx.send("No current voice connection found.")
			await ctx.message.add_reaction("⚠")


	@commands.command()
	async def say(self, ctx, *, args: str, espeak_args = []):
		"Joins the voice channel you are in and says what you passed to it"
		await ctx.message.add_reaction("🔜")

		stderr = tempfile.TemporaryFile()

		try:
			espeak = subprocess.Popen(["espeak", "--stdout", *espeak_args], stdout=subprocess.PIPE, stdin=subprocess.PIPE, stderr=stderr)
		except FileNotFoundError:
			raise ErrorWithMessage("Could not open espeak to generate voice")

		espeak.stdin.write(args.encode())
		espeak.stdin.close()

		# voice_data_wave = espeak.stdout.read()
		voice_data = discord.FFmpegOpusAudio(espeak.stdout, pipe=True)

		while espeak.poll() is None:
			await asyncio.sleep(1)
		if espeak.poll():
			stderr.seek(0)
			await ctx.send("Error: %s" % stderr.read().decode())
			await ctx.message.add_reaction("🔇")
			return

		return await self._enqueue_item(ctx, voice_data, "Say message from {}".format(ctx.message.author.nick))

		if ctx.message.guild.voice_client is not None and ctx.message.guild.voice_client.is_connected():
			voice_client = ctx.message.guild.voice_client
		else:
			voice_client = await voice_channel.connect()

		voice_client.play(voice_data)
		await ctx.message.add_reaction("✅")

	@commands.command()
	async def say_slow(self, ctx, *, args: str):
		await self.say(ctx, args=args, espeak_args = ["-s", "90"])

	@commands.command()
	async def say_fast(self, ctx, *, args: str):
		await self.say(ctx, args=args, espeak_args = ["-s", "200"])

	@commands.command()
	async def say_speed(self, ctx, speed: int, *, args: str):
		await self.say(ctx, args=args, espeak_args = ["-s", str(speed)])

	@commands.command()
	async def say_voice(self, ctx, voice: str, *, args: str):
		await self.say(ctx, args=args, espeak_args = ["-v", voice])

	headers = {
		"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv76.0) Gecko/20100101 Firefox 76.0",
	}

	@commands.command()
#@commands.check(is_owner)
	async def play(self, ctx, arg: Optional[str]):
		"Joins the voice channel you are in and plays what you passed to it"
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

		await self._enqueue_item(ctx, voice_data, "A file uploaded by {}".format(ctx.message.author.nick))

	@commands.command()
	async def yt(self, ctx, arg: str):
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

		voice_data = discord.FFmpegOpusAudio(filename, pipe=False)

		await self._enqueue_item(
			ctx,
			voice_data,
			"A youtube video chosen by {}".format(ctx.message.author.nick),
			callbacks=[(lambda: os.remove(filename))]
		)

	@commands.command()
	async def ytsearch(self, ctx, *, arg: str):
		await self.yt(ctx, "ytsearch: {}".format(arg))


def setup(bot):
	bot.add_cog(VoiceCog(bot))

def teardown(bot):
	bot.remove_cog("VoiceCog")
