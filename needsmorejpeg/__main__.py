#!/usr/bin/env python3

from .bot import bot
from . import commands

if __name__ == "__main__":
	token_file = open("secret.txt", "r")
	token = token_file.readline().strip()
	token_file.close()
	bot.run(token)

