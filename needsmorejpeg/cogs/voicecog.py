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
from collections import defaultdict

from ..errorwithmessage import ErrorWithMessage

headers = {
	"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:76.0) Gecko/20100101 Firefox/76.0",
}

class QueueItem:
	def __init__(self, get_voice_data_func: Callable[[], discord.AudioSource], description: str, origin_message: Optional[discord.Message]):
		self.get_voice_data_func: Callable[[], discord.AudioSource] = get_voice_data_func
		self.description: str = description
		self.origin_message: Optional[Discord.Message] = origin_message

class VoiceQueue:
	def __init__(self, cog):
		self.cog = cog
		self.connection: Optional[discord.VoiceClient] = None
		self.loop: bool = False
		self.now_playing: Optional[QueueItem] = None
		self.items: List[QueueItem] = []
		self.recent_error: Optional[str] = None

	@property
	def channel(self):
		return self.connection.channel if self.connection else None

	def is_connected(self) -> bool:
		return self.connection is not None

	async def connect(self, channel: discord.VoiceChannel):
		assert not self.is_connected(), ".connect called on already connected VoiceQueue {}".format(self.connection)
		self.connection = await channel.connect()

	async def disconnect(self):
		assert self.is_connected(), ".disconnect called on a not connected VoiceQueue {}".format(self.connection)
		self.loop = False
		await self.connection.disconnect()
		self.connection = None
		self.now_playing = None
		self.items = []

	def set_loop(self, loop: Optional[bool] = None):
		if loop is None:
			self.loop = not self.loop
		else:
			self.loop = loop

	async def handle_item_end(self):
		item = self.now_playing
		self.now_playing = None
		if not self.items:
			if self.loop and item is not None:
				self.enqueue(item)
			else:
				self.loop = False
				await asyncio.sleep(3)
				if self.now_playing is None:
					await self.disconnect()
		else:
			self.now_playing = self.items.pop(0)
			self.connection.play(
				self.now_playing.get_voice_data_func(),
				after = self.cog.make_async_callback(self.handle_item_end())
			)
			if self.loop and item is not None:
				self.enqueue(item)

	def enqueue(self, item):
		if self.now_playing is None:
			self.connection.play(
				item.get_voice_data_func(),
				after = self.cog.make_async_callback(self.handle_item_end())
			)
			self.now_playing = item
		else:
			self.items.append(item)

	def move_item(self, from_index: int, to_index: int):
		if from_index == 0:
			item = self.now_playing
			self.now_playing = None
			self.items.insert(to_index, item)
			self.connection.stop()
		elif to_index == 0:
			self.items.insert(0, self.now_playing)
			self.items.insert(0, self.items.pop(from_index))
			self.now_playing = None
			self.connection.stop()
		else:
			if from_index > 0: from_index -= 1 # fix index for now_playing while allowing end-relative indexing
			if to_index > 0: to_index -= 1 # fix index for now_playing while allowing end-relative indexing
			item = self.items.pop(from_index)
			self.items.insert(to_index, item)

	def remove_item(self, index: int):
		if index == 0:
			self.now_playing = None
			self.connection.stop()
		else:
			self.items.pop(index-1) # offset -1 for now_playing

	def log_error(self, err: str):
		self.recent_error = err

	def pop_error(self) -> Optional[str]:
		err = self.recent_error
		self.recent_error = None
		return err

class VoiceCog(commands.Cog):
	def __init__(self, bot):
		self.bot = bot
		self.queues: Dict[discord.Guild, VoiceQueue] = defaultdict(lambda: VoiceQueue(self))

	def make_async_callback(self, *coros) -> Callable[[object], None]:
		def callback(error) -> None:
			for coro in coros:
				if callable(coro): # This is a function, not a coroutine
					coro()
				else: # This is a coroutine
					asyncio.run_coroutine_threadsafe(coro, self.bot.loop)
		return callback

	def log_error(self, ctx, err):
		self.queues[ctx.guild].log_error(err)

	@commands.command()
	async def log(self, ctx):
		err = self.queues[ctx.guild].pop_error()
		if err is not None:
			await ctx.send("Most Recent Error:\n```{}```".format(err))
		else:
			await ctx.message.add_reaction("⚠")
			await ctx.send("No recent error.")

	@commands.Cog.listener()
	async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
		if member.guild in self.queues and before.channel == self.queues[member.guild].channel:
			if before.channel is not None and after.channel != before.channel:
				# User left channel we are in, check if no non-bot users are left in the channel
				await asyncio.sleep(3) # Wait for a bit to not immediately quit if they were just rejoining
				if all(mbr.bot for mbr in before.channel.members):
					# Stop looping and leave
					await self.queues[member.guild].disconnect()

	@commands.command()
	async def loop(self, ctx, l: Optional[bool]):
		self.queues[ctx.guild].set_loop(l)
		await ctx.message.add_reaction("🔄" if self.queues[ctx.guild].loop else "✅")

	async def _enqueue_item(self, ctx, get_voice_data_func, description: str):

		queue_item = QueueItem(get_voice_data_func, description, ctx.message)

		if not self.queues[ctx.guild].is_connected():
			await self.queues[ctx.guild].connect(ctx.author.voice.channel)

		self.queues[ctx.guild].enqueue(queue_item)

	@commands.command()
	async def skip(self, ctx):
		self.queues[ctx.guild].connection.stop()
		await ctx.message.add_reaction("✅")

	@commands.command()
	async def move(self, ctx, from_ind: int, to_ind: int):
		self.queues[ctx.guild].move_item(from_ind, to_ind)
		await ctx.message.add_reaction("✅")

	@commands.command()
	async def queue(self, ctx):
		msg = "No items in queue."
		if self.queues[ctx.guild].now_playing is not None:
			msg = '\n'.join("{}: {}".format(i, item.description) for i,item in enumerate([self.queues[ctx.guild].now_playing] + self.queues[ctx.guild].items))
		await ctx.send(msg)

	@commands.command()
	async def remove(self, ctx, index: int):
		self.queues[ctx.guild].remove_item(index)
		await ctx.message.add_reaction("✅")

	@commands.command()
	async def leave(self, ctx):
		if not self.queues[ctx.guild].is_connected():
			await ctx.send("No current voice connection found.")
			await ctx.message.add_reaction("⚠")
		else:
			await self.queues[ctx.guild].disconnect()
			await ctx.message.add_reaction("✅")


	@commands.command()
	async def say(self, ctx, *, args: str, espeak_args = []):
		"Joins the voice channel you are in and says what you passed to it"
		await ctx.message.add_reaction("🔜")

		stderr = tempfile.TemporaryFile()
		stdout = tempfile.TemporaryFile()

		try:
			espeak = subprocess.Popen(["espeak", "--stdout", *espeak_args], stdout=stdout, stdin=subprocess.PIPE, stderr=stderr)
		except FileNotFoundError:
			raise ErrorWithMessage("Could not open espeak to generate voice")

		espeak.stdin.write(args.encode())
		espeak.stdin.close()
		while espeak.poll() is None:
			await asyncio.sleep(1)
		if espeak.poll() != 0:
			await ctx.message.add_reaction("⚠")
			await ctx.send("Espeak exited unsuccessfully ({})".format(espeak.poll()))
			stderr.seek(0)
			self.log_error(ctx, stderr.read().decode())
			return
		stdout.seek(0)
		data_bytes = stdout.read()

		# voice_data_wave = espeak.stdout.read()
		def make_voice_data():
			data_file = tempfile.TemporaryFile()
			data_file.write(data_bytes)
			data_file.seek(0)
			return discord.FFmpegOpusAudio(data_file, pipe=True)

		await ctx.message.add_reaction("💾")

		await self._enqueue_item(ctx, make_voice_data, "Say message from {}".format(ctx.message.author.nick or ctx.message.author.name))

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
	async def play(self, ctx, arg: Optional[str]):
		"Joins the voice channel you are in and plays what you passed to it"
		await ctx.message.add_reaction("🔜")

		if ctx.message.attachments:
			data_bytes = await ctx.message.attachments[0].read()
			description = "A file uploaded by {} ({})".format(ctx.message.author.nick or ctx.message.author.name, ctx.message.attachments[0].filename)
		else:
			request = urllib.request.Request(arg, None, headers=headers)
			try:
				response = urllib.request.urlopen(request)
			except urllib.error.URLError:
				await ctx.message.add_reaction("⚠")
				await ctx.send("Could not download file. (invalid url)")
				return
			if not response:
				await ctx.message.add_reaction("⚠")
				await ctx.send("Could not download file. (code {})".format(response.code))
				return
			data_bytes = response.read()
			description = "A file chosen by {} ({})".format(ctx.message.author.nick or ctx.message.author.name, arg)

		def make_voice_data():
			data_file = tempfile.TemporaryFile()
			data_file.write(data_bytes)
			data_file.seek(0)
			return discord.FFmpegOpusAudio(data_file, pipe=True)

		await ctx.message.add_reaction("💾")

		await self._enqueue_item(ctx, make_voice_data, description)

	@commands.command()
	async def yt(self, ctx, arg: str):
		"Joins the voice channel you are in and plays what you passed to it"

		if arg.startswith('-') or not (arg.startswith('http') or arg.startswith('ytsearch:')):
			await ctx.send("Invalid URL")
			raise ValueEroor

		file = tempfile.NamedTemporaryFile(suffix=".mp3")
		stderr = tempfile.TemporaryFile()

		await ctx.message.add_reaction("🔜")

		ytdl = subprocess.Popen(
			["youtube-dl", arg, "--no-playlist", "--no-continue", "-f", "bestaudio", "--extract-audio", "--audio-format", "mp3", "-o", file.name],
			stderr=stderr
		)
		while ytdl.poll() is None:
			await asyncio.sleep(1)
		if ytdl.poll() != 0:
			await ctx.message.add_reaction("⚠")
			await ctx.send("Youtube-dl exited unsuccessfully ({})".format(ytdl.poll()))
			stderr.seek(0)
			self.log_error(ctx, stderr.read().decode())
			return

		make_voice_data = lambda: discord.FFmpegOpusAudio(file.name, pipe=False)

		await ctx.message.add_reaction("💾")

		await self._enqueue_item(
			ctx,
			make_voice_data,
			"A youtube video chosen by {} ({})".format(ctx.message.author.nick or ctx.message.author.name, arg)
		)

	@commands.command()
	async def ytsearch(self, ctx, *, arg: str):
		await self.yt(ctx, "ytsearch: {}".format(arg))

	def cog_unload(self):
		for g, q in self.queues.items():
			asyncio.run_coroutine_threadsafe(
				q.disconnect(),
				self.bot.loop
			)


def setup(bot):
	bot.add_cog(VoiceCog(bot))

def teardown(bot):
	bot.remove_cog("VoiceCog")
