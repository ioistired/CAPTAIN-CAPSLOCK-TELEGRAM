#!/usr/bin/env python3
# encoding: utf-8

import asyncio
import json
import random
import sys
from unicodedata import category as unicode_category

import discord


UPPERCASE_LETTERS = set()
for c in map(chr, range(sys.maxunicode+1)):
	if unicode_category(c) == 'Lu':
		UPPERCASE_LETTERS.add(c)
UPPERCASE_LETTERS = frozenset(UPPERCASE_LETTERS)
del c
client = discord.AutoShardedClient()

@client.event
async def on_ready():
	load_shouts()
	client.loop.create_task(save_shouts_loop())
	print('Ready')

@client.event
async def on_message(message):
	if not is_shout(message.content) or message.author.bot:
		return

	if shouts:
		await message.channel.send(random.choice(shouts))
	add_shout(message.content)

def is_shout(str):
	length = len(str)
	if length < 2: return False

	sum = 0
	for c in str:
		if c in UPPERCASE_LETTERS:
			sum += 1
	return (sum / length) > 0.5

def add_shout(shout):
	if shout not in shouts_set:
		shouts.append(shout)
	shouts_set.add(shout)

def load_shouts():
	global shouts, shouts_set
	shouts = []
	shouts_set = set()

	try:
		with open('shouts.txt') as f:
			for shout in json.load(f):
				add_shout(shout)
	except FileNotFoundError:
		pass

def save_shouts():
	with open('shouts.txt', 'w') as f:
		json.dump(shouts, f, ensure_ascii=False, indent=0)

async def save_shouts_loop():
	while not client.is_closed():
		save_shouts()
		await asyncio.sleep(300)


if __name__ == '__main__':
	import os

	client.run(os.environ['LOUDBOT_TOKEN'])
	save_shouts()

