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
import numpy as np

from ..bot import bot, ErrorWithMessage
from ..image_manipulator import image_manipulator, limit_size

@image_manipulator(names=["jpg", "jpeg"], argtypes=())
def jpeg(image: PIL.Image.Image) -> PIL.Image.Image:
	"JPEG Compress an image with lowest quality"
	outfile = io.BytesIO()
	image.convert("RGB").save(outfile, format="JPEG", quality=1)
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
		raise ErrorWithMessage("Cannot have a negative zoom factor")
	if zoom_factor >= 100:
		zoom_factor /= 100
	width, height = image.size
	
	new_width, new_height = width / zoom_factor, height / zoom_factor
	
	return image.crop(((width - new_width)/2, (height - new_height)/2, (width + new_width)/2, (height + new_height)/2))

@image_manipulator(argtypes=())
def invert(image: PIL.Image.Image) -> PIL.Image.Image:
	"Invert the colors of an image"
	# return PIL.ImageOps.invert(image) # doesn't work with alpha channel
	# https://stackoverflow.com/a/11491499/5142683
	arr = np.array(image)
	arr[:,:,0:3] = 255 - arr[:,:,0:3]
	return PIL.Image.fromarray(arr)

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

color_names = {
	"red": "FF0000",
	"orange": "FF8000",
	"yellow": "FFFF00",
	"lime": "80FF00",
	"green": "00FF00",
	"creamgreen": "00FF80",
	"cyan": "00FFFF",
	"denim": "0080FF",
	"blue": "0000FF",
	"purple": "8000FF",
	"magenta": "FF00FF",
	"hotpink": "FF0080",

	"darkmode": "36393F",
}

hue_range = 32.0

def hue(rgb: "Sequence[int, int, int, ...]") -> int:
	"Hue of a color in range [0,255]"
	return  PIL.Image.new("RGB", (1,1), rgb[:3]).convert("HSV").getpixel((0,0))[0]

def parse_color(color_: str) -> Tuple[int, int, int]:
	color = color_
	if color[:1] == '#':
		color = color[1:]
	if not (set(color.upper()) <= {*"0123456789ABCDEF"}):
		if color in color_names:
			color = color_names[color]
		else:
			raise ErrorWithMessage("Unrecognized color: %s" % color_)
	if len(color) == 3:
		color = color[0]*2 + color[1]*2 + color[2]*2
	if len(color) != 6:
		raise ErrorWithMessage("Unrecognized color: %s" % color_)
	return tuple(int(color[i:i+2], 16) for i in (0,2,4))

@image_manipulator(argtypes=())
def saturate(image: PIL.Image.Image) -> PIL.Image.Image:
	"Saturate all colors in an image."
	arr = np.array(image.convert("HSV"))
	arr[:,:,1] = np.minimum(arr[:,:,1]*2., 255)
	new_image = PIL.Image.fromarray(arr, mode="HSV").convert("RGB")
	if 'A' in image.mode:
		new_image.putalpha(image.getchannel('A'))
	return new_image

@image_manipulator(argtypes=(str,))
def highlight(image: PIL.Image.Image, color: str) -> PIL.Image.Image:
	"Highlight a particular color in an image"
	color = parse_color(color)

	h = hue(color)

	h_low = (h - hue_range) % 255
	h_high = (h + hue_range) % 255

	arr = np.array(image.convert("HSV"))
	if h_low > h_high:
		bad_hues = np.logical_and(arr[:,:,0] > h_high, arr[:,:,0] < h_low)
	else:
		bad_hues = np.logical_or(arr[:,:,0] > h_high, arr[:,:,0] < h_low)
	arr[:,:,1][bad_hues] = 0
	new_image = PIL.Image.fromarray(arr, mode="HSV").convert("RGB")
	if 'A' in image.mode:
		new_image.putalpha(image.getchannel('A'))
	return new_image

@image_manipulator(argtypes=(str,), names=("highlight_fade", "highlight_beta"))
def highlight_beta(image: PIL.Image.Image, color: str) -> PIL.Image.Image:
	"Highlight a particular color in an image"
	color = parse_color(color)

	h = hue(color)

	arr = np.array(image.convert("HSV"))

	hue_closenesses = abs(np.array(arr[:,:,0] - h, dtype="int8")) / 127.
	hue_closenesses = 1 - hue_closenesses

	arr[:,:,1] = arr[:,:,1] * hue_closenesses
	new_image = PIL.Image.fromarray(arr, mode="HSV").convert("RGB")
	if 'A' in image.mode:
		new_image.putalpha(image.getchannel('A'))
	return new_image

@image_manipulator(argtypes=(str,))
def tint(image: PIL.Image.Image, color: str) -> PIL.Image.Image:
	"Tint an image to a particular color"
	color = parse_color(color)

	h = hue(color)

	arr = np.array(image.convert("HSV"))
	arr[:,:,0] = int(h)
	new_image = PIL.Image.fromarray(arr, mode="HSV").convert("RGB")
	if 'A' in image.mode:
		new_image.putalpha(image.getchannel('A'))
	return new_image

@image_manipulator(argtypes=(int,))
def hueshift(image: PIL.Image.Image, amount: int) -> PIL.Image.Image:
	"Hue shift an image. Hues range from [0, 255]."

	arr = np.array(image.convert("HSV"))
	arr[:,:,0] += amount
	new_image = PIL.Image.fromarray(arr, mode="HSV").convert("RGB")
	if 'A' in image.mode:
		new_image.putalpha(image.getchannel('A'))
	return new_image

@image_manipulator(names=["crush", "crunch"], argtypes=(float,))
def crunch(image: PIL.Image.Image, degrees: float) -> PIL.Image.Image:
	"Rotate an image a number of degrees, jpeg it, rotate it again in the opposite direction, jpeg it, then zoom in to the original size."
	degrees %= 360
	image = image.rotate(degrees, expand=True)
	image = jpeg(image)
	image = image.rotate(-degrees, expand=True)
	image = jpeg(image)
	radians = math.radians(degrees)
	return zoom(image, (abs(math.sin(radians)) + abs(math.cos(radians))) ** 2) # square the scale factor since the rotation happens twice
