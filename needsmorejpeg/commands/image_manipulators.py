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
import math # sin/cos

from ..bot import bot
from ..image_manipulator import image_manipulator

@image_manipulator(names=["jpg", "jpeg"], argtypes=())
def jpeg(image: PIL.Image.Image) -> PIL.Image.Image:
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
	"Zoom in to an image (centered at the center).\nArgument is a percentage greater than or equal to 100 (without the %), or a scale factor less than 100."
	if zoom_factor <= 0:
		raise ValueError("Negative zoom value")
	if zoom_factor >= 100:
		zoom_factor /= 100
	width, height = image.size
	
	new_width, new_height = width / zoom_factor, height / zoom_factor
	
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


@image_manipulator(names=["crush", "crunch"], argtypes=(float,))
def crunch(image: PIL.Image.Image, degrees: float) -> PIL.Image.Image:
	"Rotate an image a number of degrees, jpeg it, rotate it again in the opposite direction, jpeg it, then zoom in to the original size."
	degrees %= 360
	image = image.rotate(degrees, expand=True)
	image = jpeg(image)
	image = image.rotate(-degrees, expand=True)
	image = jpeg(image)
	radians = math.radians(degrees)
	return zoom(image, (math.sin(radians) + math.cos(radians)) ** 2) # square the scale factor since the rotation happens twice
