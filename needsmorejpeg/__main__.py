#!/usr/bin/env python3

import sys
from .bot import bot
from . import commands

if __name__ == "__main__":
	if len(sys.argv) > 1 and sys.argv[1] == "--dev":
		token_file = open("secret_dev.txt", "r")
	else:
		token_file = open("secret_main.txt", "r")
	token = token_file.readline().strip()
	token_file.close()
	bot.run(token)

