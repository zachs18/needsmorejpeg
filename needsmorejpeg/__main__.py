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

from .bot import bot
from . import commands

if __name__ == "__main__":
	token_file = open("secret.txt", "r")
	token = token_file.readline().strip()
	token_file.close()
	bot.run(token)

