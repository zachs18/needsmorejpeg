#!/usr/bin/env python3

import discord
from discord.ext import commands
import PIL.Image
import io
import urllib.request

bot = commands.Bot(command_prefix=">")

def is_it_me(ctx) -> bool:
	return bot.is_owner(ctx.message.author)

@bot.command()
@commands.check(is_it_me)
async def quit(ctx):
	await ctx.send("Goodbye")
	await ctx.bot.logout()

@bot.command()
async def whoami(ctx):
	member = ctx.message.author
	await ctx.send("You are {} on this server, {} globally, and have id {}. ".format(
			member.nick or member.name, member.name + "#" + member.discriminator, member.id)
	)

@bot.command()
async def ping(ctx):
	await ctx.send("pong")

headers = {
	"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:76.0) Gecko/20100101 Firefox/76.0",
}

@bot.command()
async def jpeg(ctx, *args):
	async with ctx.typing():
		quality = 10
		if len(args) > 0:
			try:
				quality = int(args[0])
				args = args[1:]
			except ValueError:
				pass

		def make_file_from_bytes(bs: bytes, filename: str) -> "discord.File":
			infile = io.BytesIO(bs)
			im = PIL.Image.open(infile).convert('RGB')
			outfile = io.BytesIO()
			im.save(outfile, quality=quality, optimize=True, progressive=True, format="JPEG")
			outfile.seek(0)
			return discord.File(outfile, filename=filename)

		async def show_error(*args):
			print(*args)
			await ctx.send(' '.join(map(str, args)))

		files = []
		for attachment in ctx.message.attachments:
			try:
				files.append(make_file_from_bytes(await attachment.read(), attachment.filename + ".jpeg"))
			except discord.DiscordException as ex:
				await show_error(ex)
		for url in args:
			try:
				request = urllib.request.Request(url, None, headers)
				response = urllib.request.urlopen(request)
				if not response:
					await show_error('`' + url + '`', "failed")
					continue
				files.append(make_file_from_bytes(response.read(), "image0.jpeg"))
			except Exception as ex:
				await show_error('`' + url + '`', 'failed:', ex)

		if not files: # search through history for most recent message with (an) image(s)
			async for msg in ctx.history():
				if msg.attachments:
					for attachment in msg.attachments:
						try:
							files.append(make_file_from_bytes(await attachment.read(), attachment.filename + ".jpeg"))
						except discord.DiscordException as ex:
							await show_error(ex)
					if files:
						break
				else:
					urls = [word for word in msg.content.split() if word.startswith('http://')]
					for url in urls:
						try:
							request = urllib.request.Request(url, None, headers)
							response = urllib.request.urlopen(request)
							if not response:
								await show_error('`' + url + '`', "failed")
								continue
							files.append(make_file_from_bytes(response.read(), "image0.jpeg"))
						except Exception as ex:
							await show_error('`' + url + '`', 'failed:', ex)
					if files:
						break

		if files:
			await ctx.send("Here you go!", files=files)
		else:
			await ctx.send("No images found to jepg-ify!", files=files)


if __name__ == "__main__":
	token_file = open("secret.txt", "r")
	token = token_file.readline().strip()
	token_file.close()
	bot.run(token)

