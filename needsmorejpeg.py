#!/usr/bin/env python3
from typing import Optional, List, Tuple, Callable, Dict, Union
import discord
from bs4 import BeautifulSoup as BS
from discord.ext import commands
import PIL.Image
import PIL.ImageOps
import PIL.ImageFilter
import io
import asyncio
import urllib.request
import random

bot = commands.Bot(command_prefix=">", activity=discord.Game("use >jpeg"))

def is_it_me(ctx) -> bool:
	return bot.is_owner(ctx.message.author)

@bot.event
async def on_command_error(ctx, error):
	if isinstance(error, discord.ext.commands.CommandNotFound):
		return
	if isinstance(error.__cause__, discord.errors.Forbidden):
		await ctx.message.add_reaction("⛔")
	await ctx.message.add_reaction("⚠")
	raise error

def limit_size(image: PIL.Image.Image, maxsize: int = 4000 * 4000) -> PIL.Image.Image:
	width, height = image.size
	size = width * height
	if size < maxsize:
		return image
	else:
		scale = maxsize / size
		return image.resize((int(width * scale), int(height * scale)))

@bot.command(hidden=True)
@commands.check(is_it_me)
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

headers = {
	"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:76.0) Gecko/20100101 Firefox/76.0",
}

Image_with_info = Tuple[PIL.Image.Image, discord.Member, str]

def make_file_from_image(image: PIL.Image.Image, filename: str, *, quality: int = 100, format: str = "JPEG") -> discord.File:
	"Convert a PIL.Image.Image to a discord.File with the specified @kwparam format and @kwparam quality"
	outfile = io.BytesIO()
	image.save(outfile, quality=quality, optimize=True, progressive=True, format=format)
	outfile.seek(0)
	file = discord.File(outfile, filename + ".jpeg")
	return file
	
	
def make_image_from_bytes(bs: bytes) -> PIL.Image.Image:
	infile = io.BytesIO(bs)
	image = PIL.Image.open(infile).convert("RGB")
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
			images.append((image, message.author, "{0}.jpeg".format(attachment.filename)))
		except discord.DiscordException:
			raise
	for embed in message.embeds:
		if embed.image:
			url: str = embed.image.url
			try:
				image = make_image_from_url(url)
				images.append((image, message.author, "image0.jpeg"))
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
				images.append((image, message.author, "image0.jpeg"))
			except ValueError as ve: # unknown url type
				#print(141, ve)
				pass
			except PIL.UnidentifiedImageError as ex:
				if not ignore_exceptions:
					raise PIL.UnidentifiedImageError(url)
	return images

async def get_avatar_image(member: discord.Member) -> Image_with_info:
	image = make_image_from_bytes(await member.avatar_url.read())
	return (image, member, "{0}.jpeg".format(member.id))

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

@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
	if payload.user_id == bot.user.id: # ignore our own reactions
		return
	if payload.emoji.name != "❌":
		return
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
	
def command_from_image_manipulator(func: Callable[[PIL.Image.Image], PIL.Image.Image], /, argtypes: Optional[Tuple] = ()):
	if func is None:
		raise ValueError
	async def command(ctx: discord.ext.commands.Context, *args):
		if argtypes:
			args = [typ(arg) for typ, arg in zip(argtypes, args)]
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

def image_manipulator(func: "Optional[Callable[[PIL.Image.Image, ...], PIL.Image.Image]]" = None, \
					  *, \
					  name: Optional[str] = None, \
					  names: Optional[List[str]] = None, \
					  args: Optional[Tuple] = ()
					 ):
	if func is None:
		def wrapper(f: "Callable[[PIL.Image.Image, ...], PIL.Image.Image]" = None):
			return image_manipulator(f, name=name, names=names, args=args)
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
		image_manipulators[name] = (func, args)
		bot.command(name=name)(command_from_image_manipulator(func, argtypes=args))
	return func

@image_manipulator(names=["jpg", "jpeg"])
def jpeg_beta(image: PIL.Image.Image) -> PIL.Image.Image:
	"JPEG Compress an image with lowest quality"
	outfile = io.BytesIO()
	image.save(outfile, format="JPEG", quality=1)
	outfile.seek(0)
	return PIL.Image.open(outfile)

@image_manipulator
def rotate180(image: PIL.Image.Image) -> PIL.Image.Image:
	"Rotate an image 180 degrees (DEPRECATED)"
	return image.rotate(180)

@image_manipulator(args=(float,))
def rotate(image: PIL.Image.Image, degrees: float) -> PIL.Image.Image:
	"Rotate an image a number of degrees."
	return image.rotate(degrees, expand=True)

@image_manipulator(args=(float,))
def zoom(image: PIL.Image.Image, zoom_factor: float) -> PIL.Image.Image:
	"Zoom in to an image (centered at the center).\nArgument is a percentage (without the %)."
	if zoom_factor <= 0:
		raise ValueError("Negative zoom value")
	if zoom_factor < 100:
		zoom_factor *= 100
	width, height = image.size
	
	new_width, new_height = width * 100 / zoom_factor, height * 100 / zoom_factor
	
	return image.crop(((width - new_width)/2, (height - new_height)/2, (width + new_width)/2, (height + new_height)/2))

@image_manipulator
def invert(image: PIL.Image.Image) -> PIL.Image.Image:
	"Invert the colors of an image"
	return PIL.ImageOps.invert(image)

@image_manipulator
def hflip(image: PIL.Image.Image) -> PIL.Image.Image:
	"Flip an image horizontally"
	return PIL.ImageOps.flip(image.rotate(90, expand=True)).rotate(-90, expand=True)

@image_manipulator
def vflip(image: PIL.Image.Image) -> PIL.Image.Image:
	"Flip an image vertically"
	return PIL.ImageOps.flip(image)

@image_manipulator
def blur(image: PIL.Image.Image) -> PIL.Image.Image:
	"Blur an image"
	return image.filter(PIL.ImageFilter.BLUR)

@bot.command()
async def manipulate(ctx, *args: str):
	"Manipulate an image (docs todo)"
	
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
		images = await find_images_from_context(ctx, ignore_first_text = (len(argtypes)>0))
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

@bot.command()
async def castlevania(ctx):
	"Generates a random Castlevania game title (credit to BDG).\nhttps://www.youtube.com/watch?v=STFAzuCxAXE&t=441"
	first_parts = [
		"Sonata",
		"Waltz",
		"Twilight",
		"Paso Doble",
		"Recitative",
		"Polyphony",
		"Melody",
		"Impression",
		"Minuet",
		"Congregation",
		"Overture",
		"Jazz Solo"
	]

	second_parts = [
		"Solitude",
		"Sadness",
		"Pain",
		"Despair",
		"Flame",
		"Frightenment",
		"a Foggy Night",
		"Depression",
		"Bad Shit Goin' Down",
		"Ruin",
		"Unease",
		"a Rejection Letter from Your Dream Job",
		"Dissonance",
		"Melancholy",
		"Apprehension",
		"Anxiety",
		"the Night",
		"Difficult Talks With Your Father",
		"Shadows",
		"a Real Shitty Day",
		"Gloom",
		"Unpleasent Odors",
		"Despondency",
		"Broken Bones",
		"Sorrow",
		"Angst",
		"That Feeling When Your Toes Go All Tingly and Numb",
		"the Eclipse",
		"Darkness",
		"Disquiet"
	]

	cursive = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", "𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃")

	game_name = "Castlevania: {0} of {1}".format(random.choice(first_parts), random.choice(second_parts))
	game_name = game_name.translate(cursive)
	message = "Your Castlevania game name is \"{0}\".\n`Credit to BDG https://youtu.be/STFAzuCxAXE?t=441`".format(game_name)
	await ctx.send(message)


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

if __name__ == "__main__":
	token_file = open("secret.txt", "r")
	token = token_file.readline().strip()
	token_file.close()
	bot.run(token)

