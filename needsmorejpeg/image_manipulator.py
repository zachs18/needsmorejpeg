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

from .bot import bot

def limit_size(image: PIL.Image.Image, maxsize: int = 4000 * 4000) -> PIL.Image.Image:
	width, height = image.size
	size = width * height
	if size < maxsize:
		return image
	else:
		scale = maxsize / size
		return image.resize((int(width * scale), int(height * scale)))

headers = {
	"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:76.0) Gecko/20100101 Firefox/76.0",
}

Image_with_info = Tuple[PIL.Image.Image, discord.Member, str]

def make_file_from_image(image: PIL.Image.Image, filename: str, *, quality: int = 100, format: str = "PNG") -> discord.File:
	"Convert a PIL.Image.Image to a discord.File with the specified @kwparam format and @kwparam quality"
	outfile = io.BytesIO()
	image.save(outfile, quality=quality, optimize=True, progressive=True, format=format)
	outfile.seek(0)
	file = discord.File(outfile, filename + "." + format)
	return file

def make_image_from_bytes(bs: bytes) -> PIL.Image.Image:
	infile = io.BytesIO(bs)
	image = PIL.Image.open(infile).convert("RGBA")
	image = PIL.ImageOps.exif_transpose(image)
	return image

def make_image_from_url(url: str) -> PIL.Image.Image:
	request = urllib.request.Request(url, None, headers)
	response = urllib.request.urlopen(request)
	if not response:
		raise FileNotFoundError(url)
	try:
		return make_image_from_bytes(response.read())
	except PIL.UnidentifiedImageError as ex:
		soup = BS(response)
		for img_tag in soup.find_all('img'):
		# ) if img_src.startswith("https://") or img_src.startswith("http://")):
			img_src = img_tag['src']
			if img_src.startswith("https://") or img_src.startswith("http://"):
				try:
					request = urllib.request.Request(img_src, None, headers)
					response = urllib.request.urlopen(request)
					if not response:
						continue
					return make_image_from_bytes(response.read())
				except PIL.UnidentifiedImageError as ex:
					continue
	raise ValueError("webpage at url did not contain any valid <img> tags")

async def get_images_from_message(message: discord.Message, *, ignore_text: bool = False, ignore_exceptions: bool = True) -> List[Image_with_info]:
	images: List[Image_with_info] = []
	for attachment in message.attachments:
		try:
			image = make_image_from_bytes(await attachment.read())
			images.append((image, message.author, str(attachment.filename)))
		except discord.DiscordException:
			raise
	for embed in message.embeds:
		if embed.image:
			url: str = embed.image.url
			try:
				image = make_image_from_url(url)
				images.append((image, message.author, "image0"))
			except (discord.DiscordException, FileNotFoundError) as ex:
				if not ignore_exceptions:
					raise ex
			except PIL.UnidentifiedImageError:
				if not ignore_exceptions:
					raise PIL.UnidentifiedImageError(url)
	if not ignore_text:
		for url in message.content.split():
			if not url.startswith('http'):
				continue
			try:
				image = make_image_from_url(url)
				images.append((image, message.author, "image0"))
			except ValueError as ve: # unknown url type
				#print(141, ve)
				pass
			except PIL.UnidentifiedImageError as ex:
				if not ignore_exceptions:
					raise PIL.UnidentifiedImageError(url)
	return images

async def get_avatar_image(member: discord.Member) -> Image_with_info:
	image = make_image_from_bytes(await member.avatar_url.read())
	return (image, member, str(member.id))

async def find_images_from_context(ctx, *, ignore_first_text: bool = False) -> List[Image_with_info]:
	message = ctx.message
	images: "List[Image_with_info]" = []
	try:
		images += await get_images_from_message(message, ignore_text=ignore_first_text, ignore_exceptions=False) # don't ignore errors for the first one
	except FileNotFoundError as ex:
		await ctx.send("Could not find: {}".format(ex.args[0]))
		raise ex
	except PIL.UnidentifiedImageError as ex:
		await ctx.send("Not an image: {}".format(ex.args[0]))
		raise ex
	images += [await get_avatar_image(member) for member in message.mentions] # Only look for mentions in the first message
	if not images:
		async for message in ctx.history():
			images += await get_images_from_message(message)
			if images:
				break
	return images


def command_from_image_manipulator(func: Callable[[PIL.Image.Image], PIL.Image.Image], /, argtypes: Tuple = ()):
	if func is None:
		raise ValueError
	async def command(ctx: discord.ext.commands.Context, *args):
		if argtypes:
			args = tuple([typ(arg) for typ, arg in zip(argtypes, args)])
		else:
			args = ()
		async with ctx.typing():
			images = await find_images_from_context(ctx, ignore_first_text = (len(argtypes)>0))
			for image, author, filename in images:
				#print(args)
				#modified_image = func(image, *args)
				modified_image = limit_size(func(image, *args))
				file = make_file_from_image(modified_image, filename=filename)
				# allowed_mentions = discord.AllowedMentions(everyone = False, users = False, roles = False)
				# message = await ctx.send("{0} or {1} may delete this by reacting ❌".format(ctx.message.author.mention, author.mention), file=file, allowed_mentions=allowed_mentions)
				message = await ctx.send("{0} or {1} may delete this by reacting ❌".format(ctx.message.author.mention, author.mention), file=file)
				await message.add_reaction("❌")
	command.__name__ = func.__name__
	command.__doc__ = func.__doc__
	return command

image_manipulators: Dict[str, Tuple[Callable[[PIL.Image.Image], PIL.Image.Image], Tuple]] = {}

# Note, func should really be
# Optional[Union[
#     Callable[[PIL.Image.Image], PIL.Image.Image],
#     Callable[[PIL.Image.Image, str], PIL.Image.Image],
#     Callable[[PIL.Image.Image, float], PIL.Image.Image],
#     Callable[[PIL.Image.Image, int], PIL.Image.Image],
#     # etc.
#     Callable[[PIL.Image.Image, str, str], PIL.Image.Image],
#     Callable[[PIL.Image.Image, str, float], PIL.Image.Image],
#     # etc.
#     Callable[[PIL.Image.Image, str, str, str], PIL.Image.Image]
#     # etc.
# ], but that is not representable
def image_manipulator(func: Optional[Callable[..., PIL.Image.Image]] = None, \
					  *, \
					  name: Optional[str] = None, \
					  names: Optional[List[str]] = None, \
					  argtypes: Optional[Tuple] = ()
					 ):
	if func is None:
		def wrapper(f: "Callable[[PIL.Image.Image, ...], PIL.Image.Image]" = None):
			return image_manipulator(f, name=name, names=names, argtypes=argtypes)
		return wrapper
	import inspect
	if inspect.iscoroutinefunction(func):
		raise TypeError("image_manipulators should not be async")
	
	if name is None and names is None:
		names = [func.__name__]
	elif name is not None and names is not None:
		raise TypeError("cannot specify both name and names keyword arguments")
	elif name is not None:
		names = [name]
	
	for name in names:
		image_manipulators[name] = (func, argtypes)
		bot.command(name=name)(command_from_image_manipulator(func, argtypes=argtypes))
	return func # So the function can be used elsewhere

@bot.command()
async def manipulate(ctx, *args: str):
	"""Manipulate an image
	Any sequence of image manipulation commands (e.g. invert, jpeg, rotate <degrees>) may be used.
	Syntax:
	>manipulate <command1> [command1 args (if any)] [<command1> [command2 args (if any)]] ...
	Example:
	>manipulate rotate 45 jpeg invert rotate -45
	"""
	def applier(*funcs):
		async def apply(image):
			for f in funcs:
				#image = f(image)
				await asyncio.sleep(0)
				image = limit_size(f(image))
			return image
		return apply
	
	funcs = []
	
	i: int = 0
	while i < len(args):
		try:
			manipulator, argtypes = image_manipulators[args[i]]
		except KeyError:
			await ctx.message.add_reaction("⚠")
			await ctx.send("Unknown image manipulator: {}".format(args[i]), delete_after=5)
			return
		func_args = []
		for j, typ in enumerate(argtypes):
			try:
				func_args.append(typ(args[i + 1 + j]))
			except ValueError:
				await ctx.message.add_reaction("⚠")
				await ctx.send("Invalid argument #{} for manipulator {}: {} (expected {})" \
							   	.format(j, args[i], repr(args[i + j]), typ),
							   delete_after=5)
				return
			except IndexError:
				await ctx.message.add_reaction("⚠")
				await ctx.send("Not enough arguments for manipulator {}: got {} (expected {})" \
							   	.format(args[i], j, len(argtypes)),
							   delete_after=5)
				return
		#print(i, args[i], len(argtypes), func_args)
		i += 1 + len(argtypes)
		funcs.append(lambda image, func_args=func_args, manipulator=manipulator: manipulator(image, *func_args))
	
	func = applier(*funcs)
	await ctx.message.add_reaction("🔜")
	async with ctx.typing():
		images = await find_images_from_context(ctx, ignore_first_text = True)
		for image, author, filename in images:
			#print(args)
			modified_image = await func(image)
			file = make_file_from_image(modified_image, filename=filename)
			# allowed_mentions = discord.AllowedMentions(everyone = False, users = False, roles = False)
			# message = await ctx.send("{0} or {1} may delete this by reacting ❌".format(ctx.message.author.mention, author.mention), file=file, allowed_mentions=allowed_mentions)
			message = await ctx.send("{0} or {1} may delete this by reacting ❌".format(ctx.message.author.mention, author.mention), file=file)
			await message.add_reaction("❌")
	await ctx.message.remove_reaction("🔜", bot.user)

@bot.command()
async def delete(ctx, message: Optional[discord.Message] = None):
	"To delete a message posted by this bot, run `>delete message_link` where `message_link` is the link to\
	the message you want to delete (accessible by `copy message link` in the right-click menu on a message)."
	if message is None:
		await ctx.send("To delete a message posted by this bot, run `>delete message_link` where `message_link` is the link to the message you want to delete (accessible by `copy message link` in the right-click menu on a message).")
		await ctx.message.add_reaction("⚠")
	elif message.author != ctx.me:
		await ctx.send("That message was not posted by this bot.", delete_after=10)
		await ctx.message.add_reaction("⚠")
		return
	elif ctx.message.author not in message.mentions:
		await ctx.send("As far as I can tell, that message's image was not requested nor originally posted by you ({0}).\nIf you believe this to be an error, please contact {1}.".format(ctx.message.author.mention, ctx.message.guild.get_member(author_id).mention), delete_after=10)
		await ctx.message.add_reaction("⚠")
		return
	else:
		try:
			await message.delete()
		except discord.DiscordException as ex:
			print(ex, "while deleting message with id ", message_id)
			await ctx.send("Could not delete message.")
			await ctx.message.add_reaction("⚠")
			return
		await ctx.message.add_reaction("✔")


"""
@bot.command(name="jpeg_old")
async def jpeg(ctx, *args):
	"Convert an image to jpeg with low quality"
	async with ctx.typing():
		quality = 1
		if len(args) > 0:
			try:
				quality = int(args[0])
				if quality < 1:
					quality = 1
				if quality > 100:
					quality = 100
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

		def make_file_from_url(url: str, filename: str) -> "discord.File":
			request = urllib.request.Request(url, None, headers)
			response = urllib.request.urlopen(request)
			if not response:
				raise FileNotFoundError(url)
			return make_file_from_bytes(response.read(), filename)

		async def show_error(*args):
			print(*args)
			await ctx.send(' '.join(map(str, args)))

		files = []
		for attachment in ctx.message.attachments:
			try:
				image = make_image_from_bytes(await attachment.read())
				file = make_file_from_image(image, "{0}.jpeg".format(attachment.filename), quality = quality)
				files.append(file)
			except discord.DiscordException as ex:
				await show_error(ex)
			except Exception as ex:
				await show_error(ex)
		for embed in ctx.message.embeds:
			if embed.image:
				url: str = embed.image.url
				try:
					image = make_image_from_url(url)
					file = make_file_from_image(image, "image0.jpeg")
					files.append(file)
				except discord.DiscordException as ex:
					await show_error(ex)
				except FileNotFoundError as ex:
					await show_error('`' + url + '`', "failed (no or invalid response)")
				except PIL.UnidentifiedImageError as ex:
					await show_error('`' + url + '`', "failed (not an image)")
				except Exception as ex:
					await show_error(ex)
		for member in ctx.message.mentions:
			try:
				image = make_image_from_bytes(await member.avatar_url.read())
				file = make_file_from_image(image, "{0}.jpeg".format(member.id), quality = quality)
				files.append(file)
			except discord.DiscordException as ex:
				await show_error(ex)
			except Exception as ex:
				await show_error(ex)

		for url in args:
			if not url.startswith('http'):
				continue
			try:
				files.append(make_file_from_url(url, "image0.jpeg"))
			except PIL.UnidentifiedImageError as ex:
				await show_error('`' + url + '`', "failed (not an image)")
			except Exception as ex:
				await show_error('`' + url + '`', 'failed:', ex)

		if not files: # search through history for most recent message with (an) image(s) or url(s)
			async for msg in ctx.history():
				if msg.attachments:
					for attachment in msg.attachments:
						try:
							files.append(make_file_from_bytes(await attachment.read(), attachment.filename + ".jpeg"))
						except discord.DiscordException as ex:
							await show_error(ex)
						except PIL.UnidentifiedImageError as ex:
							await show_error('`' + attachment.filename + '`', "failed (not an image)")
					if files:
						break
				else:
					urls = [word for word in msg.content.split() if word.startswith('http://') or word.startswith("https://")]
					for url in urls:
						try:
							request = urllib.request.Request(url, None, headers)
							response = urllib.request.urlopen(request)
							if not response:
								await show_error('getting `' + url + '`', "failed (no response)")
								continue
						except Exception as ex:
							await show_error('getting `' + url + '`', 'failed (exception):', ex)
							continue

						response = response.read()

						try:
							files.append(make_file_from_bytes(response, "image0.jpeg"))
							continue
						except PIL.UnidentifiedImageError: # try html
							pass

						try:
							soup = BS(response)
							for img_src in (img_src for img_src in (img_tag['src'] for img_tag in soup.find_all('img')) if img_src.startswith("https://") or img_src.startswith("http://")):
								try:
									request = urllib.request.Request(img_src, None, headers)
									response = urllib.request.urlopen(request)
									if not response:
										continue
									response = response.read()
									files.append(make_file_from_bytes(response, "image0.jpeg"))
								except Exception as ex:
									continue
								break
						except:
							await show_error("`" + url + "` failed (not image or html)")
					if files:
						break

		if files:
			await ctx.send("Here you go!", files=files)
		else:
			await ctx.send("No images found to jepg-ify!", files=files)
"""
