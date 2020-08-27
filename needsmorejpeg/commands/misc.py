#!/usr/bin/env python3
import random

from ..bot import bot

cursive_translation = str.maketrans(
	"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789",
	"𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
)

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

	game_name = "Castlevania: {0} of {1}".format(random.choice(first_parts), random.choice(second_parts))
	game_name = game_name.translate(cursive_translation)
	message = "Your Castlevania game name is \"{0}\".\n`Credit to BDG https://youtu.be/STFAzuCxAXE?t=441`".format(game_name)
	await ctx.send(message)

@bot.command()
async def cursive(ctx, *, arg):
	"Repeats what you tell it to, but 𝓲𝓷 𝓬𝓾𝓻𝓼𝓲𝓿𝓮"
	await ctx.send(arg.translate(cursive_translation))
