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

from ..bot import bot
from ..image_manipulator import image_manipulator

@image_manipulator(names=["jpg", "jpeg"], argtypes=())
def jpeg_beta(image: PIL.Image.Image) -> PIL.Image.Image:
	"JPEG Compress an image with lowest quality"
	outfile = io.BytesIO()
	image.save(outfile, format="JPEG", quality=1)
	outfile.seek(0)
	return PIL.Image.open(outfile)

@image_manipulator(argtypes=())
def rotate180(image: PIL.Image.Image) -> PIL.Image.Image:
	"Rotate an image 180 degrees (DEPRECATED)"
	return image.rotate(180)

@image_manipulator(argtypes=(float,))
def rotate(image: PIL.Image.Image, degrees: float) -> PIL.Image.Image:
	"Rotate an image a number of degrees."
	return image.rotate(degrees, expand=True)

@image_manipulator(argtypes=(float,))
def sharpen(image: PIL.Image.Image, factor: float) -> PIL.Image.Image:
	"Sharpen an image by a factor."
	sharpener = PIL.ImageEnhance.Sharpness(image)
	return sharpener.enhance(factor)

@image_manipulator(argtypes=(float,))
def zoom(image: PIL.Image.Image, zoom_factor: float) -> PIL.Image.Image:
	"Zoom in to an image (centered at the center).\nArgument is a percentage (without the %)."
	if zoom_factor <= 0:
		raise ValueError("Negative zoom value")
	if zoom_factor < 100:
		zoom_factor *= 100
	width, height = image.size
	
	new_width, new_height = width * 100 / zoom_factor, height * 100 / zoom_factor
	
	return image.crop(((width - new_width)/2, (height - new_height)/2, (width + new_width)/2, (height + new_height)/2))

@image_manipulator(argtypes=())
def invert(image: PIL.Image.Image) -> PIL.Image.Image:
	"Invert the colors of an image"
	return PIL.ImageOps.invert(image)

@image_manipulator(argtypes=())
def hflip(image: PIL.Image.Image) -> PIL.Image.Image:
	"Flip an image horizontally"
	return PIL.ImageOps.flip(image.rotate(90, expand=True)).rotate(-90, expand=True)

@image_manipulator(argtypes=())
def vflip(image: PIL.Image.Image) -> PIL.Image.Image:
	"Flip an image vertically"
	return PIL.ImageOps.flip(image)

@image_manipulator(argtypes=())
def blur(image: PIL.Image.Image) -> PIL.Image.Image:
	"Blur an image"
	return image.filter(PIL.ImageFilter.BLUR)

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
