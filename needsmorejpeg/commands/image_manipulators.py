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

from ..bot import bot
from ..image_manipulator import image_manipulator, limit_size

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
}

hue_range = 40.0

def hue(rgb: "Sequence[int, int, int, ...]") -> float:
	"Hue of a color in degrees"
	r, g, b, *rest = rgb
	mx, mn = max(r, g, b), min(r, g, b)
	if mx == mn: # https://stackoverflow.com/a/23094494/5142683
		return 0.0
	elif r == mx: # the + 0 are to force numpy uint8s into python ints
		return (  0.0 + 60.0 * (g + 0 - b) / (mx + 0 - mn)) % 360.0
	elif g == mx:
		return (120.0 + 60.0 * (b + 0 - r) / (mx + 0 - mn)) % 360.0
	else: #if b == mx:
		return (240.0 + 60.0 * (r + 0 - g) / (mx + 0 - mn)) % 360.0

def greyscale(rgb: "Sequence[int, int, int, ...]") -> "Sequence[int, int, int, ...]":
	r, g, b, *rest = rgb
	g = int(0.30 * r + 0.59 * g + 0.11 * b)
	return [g, g, g, *rest]

@image_manipulator(argtypes=(str,))
def highlight(image: PIL.Image.Image, color: str) -> PIL.Image.Image:
	"Highlight a specific color in an image. Inefficient, so has a small size limit"
	image = limit_size(image, 640 * 640)
	
	if color[:1] == '#':
		color = color[1:]
	if not (set(color.upper()) <= {*"0123456789ABCDEF"}):
		if color in color_names:
			color = color_names[color]
		else:
			raise ValueError("unrecognized color")
	if len(color) == 3:
		color = color[0]*2 + color[1]*2 + color[2]*2
	if len(color) != 6:
		raise ValueError("unrecognized color")
	color = [int(color[i:i+2], 16) for i in [0,2,4]]
	
	h = hue(color)
	if h + hue_range >= 360.0:
		h -= 360.0
		# -hue_range <= h <= 360 - hue_range
	
	arr = np.array(image)
	if h >= hue_range and h <= 360.0 - hue_range:
		# don't need to deal with two ranges [0,x]&[360-x,360]
		for row in arr:
			for pixel in row:
				if not h - hue_range <= hue(pixel) <= h + hue_range:
					pixel[:] = greyscale(pixel)
	else:
		# do need to deal with two ranges [0,x]&[360-x,360]
		for row in arr:
			for pixel in row:
				hh = hue(pixel)
				if not (hh <= h + hue_range or h - hue_range + 360 <= hh):
					pixel[:] = greyscale(pixel)
	
	return PIL.Image.fromarray(arr)

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
