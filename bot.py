#!/usr/bin/env python3
# encoding: utf-8

import asyncio
import json
import re
import sys
from unicodedata import category as unicode_category

import asyncpg
from passlib.hash import argon2
import discord

client = discord.AutoShardedClient()

with open('data/config.json') as f:
	config = json.load(f)
del f

# a salt is required for consistent hashes,
# however, I'm not using one
# the intention of hashing is mostly to make it difficult for me to read message
# content. I do not plan on making rainbow tables to do so, and even then,
# argon2 should be good enough that they won't help me much
# if you change these parameters, you MUST clear all entries from the database.
hasher = argon2.using(parallelism=4, memory_cost=128*1024, rounds=10, salt=b'12345678')

UPPERCASE_LETTERS = set()
for c in map(chr, range(sys.maxunicode+1)):
	if unicode_category(c) == 'Lu':  # uppercase letter
		UPPERCASE_LETTERS.add(c)
UPPERCASE_LETTERS = frozenset(UPPERCASE_LETTERS)
del c

def is_shout(str):
	length = len(str)
	# "H" is not a shout
	if length < 2: return False

	# calculate the percentage of letters which are capital
	sum = 0
	for c in str:
		if c in UPPERCASE_LETTERS:
			sum += 1
	return (sum / length) > 0.5

## EVENTS

@client.event
async def on_ready():
	await load_db()
	print('Ready')

@client.event
async def on_message(message):
	if not is_shout(message.content) or message.author.bot:
		return

	shout = await get_shout()
	if shout: await message.channel.send(shout)
	message.content = sanitize(message.content)
	await save_shout(message)

@client.event
async def on_raw_message_edit(payload):
	if 'webhook_id' in payload.data or 'content' not in payload.data:
		return

	id = payload.message_id
	if not await pool.fetchval('SELECT hash FROM shout WHERE message = $1', id):
		return

	content = payload.data['content']
	if not is_shout(content):
		# don't let people sneakily insert non-shouts into the database
		await delete_shout(id)
		return

	content = sanitize(content)
	h = hasher.hash(content)
	try:
		await pool.execute('UPDATE shout SET hash = $1 WHERE message = $2', h, id)
	except asyncpg.UniqueViolationError:
		# don't store duplicate hashes
		await pool.execute('DELETE FROM shout WHERE message = $1', id)

@client.event
async def on_raw_message_delete(payload):
	await delete_shout(payload.message_id)

@client.event
async def on_raw_bulk_message_delete(payload):
	for id in payload.message_ids:
		await delete_shout(id)

@client.event
async def on_guild_channel_delete(channel):
	await pool.execute('DELETE FROM shout WHERE channel = $1', channel.id)

@client.event
async def on_guild_remove(guild):
	await pool.execute('DELETE FROM shout WHERE guild_or_user = $1', guild.id)

## DATABASE

async def save_shout(message):
	h = hasher.hash(message.content)
	await pool.execute("""
		INSERT INTO shout(hash, guild_or_user, channel, message)
		VALUES($1, $2, $3, $4)
		ON CONFLICT(hash) DO NOTHING
	""", h, getattr(message.channel, 'guild', message.author).id, message.channel.id, message.id)

async def get_shout():
	result = await pool.fetchrow("""
		SELECT guild_or_user, channel, message
		FROM shout
		ORDER BY random()
		LIMIT 1""")

	if not result:
		# probably there were no records in the db yet
		return
	thing_id, channel_id, message_id = result

	thing = client.get_guild(thing_id) or client.get_user(thing_id)
	if thing is None:
		return

	try:
		# thing is a User
		channel = thing.dm_channel
	except AttributeError:
		# thing is a Guild
		channel = thing.get_channel(channel_id)

	if channel is None:
		return

	try:
		message = await channel.get_message(message_id)
	except discord.Forbidden:
		await delete_shout(message_id)
	except discord.HTTPException:
		return

	return sanitize(message.content)

async def delete_shout(message_id):
	await pool.execute('DELETE FROM shout WHERE message = $1', message_id)

## MISC

def sanitize(s):
	# if you change this, you MUST clear all entries from the database
	s = re.sub(r'<@!?\d+>', '@SOMEONE', s, re.ASCII)
	s = re.sub(r'<@&\d+>',   '@SOME ROLE', s, re.ASCII)
	s = s.replace('@', '@\N{zero width non-joiner}')
	return s

async def load_db():
	global pool

	credentials = config['database']
	pool = await asyncpg.connect(**credentials)

	with open('data/schema.sql') as f:
		schema = f.read()

	await pool.execute(schema)


if __name__ == '__main__':
	client.run(config['tokens']['discord'])
