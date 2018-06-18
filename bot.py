#!/usr/bin/env python3
# encoding: utf-8

import asyncio
import sys
from unicodedata import category as unicode_category

import asyncpg
from passlib.hash import argon2
import discord


UPPERCASE_LETTERS = set()
for c in map(chr, range(sys.maxunicode+1)):
	if unicode_category(c) == 'Lu':
		UPPERCASE_LETTERS.add(c)
UPPERCASE_LETTERS = frozenset(UPPERCASE_LETTERS)
del c
client = discord.AutoShardedClient()
hasher = argon2.using(parallelism=4, memory_cost=128*1024, rounds=20)

@client.event
async def on_ready():
	print('Ready')

@client.event
async def on_message(message):
	if not is_shout(message.content) or message.author.bot:
		return

def is_shout(str):
	length = len(str)
	if length < 2: return False

	sum = 0
	for c in str:
		if c in UPPERCASE_LETTERS:
			sum += 1
	return (sum / length) > 0.5



if __name__ == '__main__':
	import os

	client.run(os.environ['LOUDBOT_TOKEN'])
