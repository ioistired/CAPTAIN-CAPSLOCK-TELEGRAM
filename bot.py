#!/usr/bin/env python3
# encoding: utf-8

import asyncio
import json
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
# a salt is required for consistent hashes,
# however, I'm not using one
hasher = argon2.using(parallelism=4, memory_cost=128*1024, rounds=10, salt=b'12345678')

@client.event
async def on_ready():
	await load_db()
	print('Ready')

async def load_db():
	global pool
	with open('data/config.json') as f:
		credentials = json.load(f)['database']

	pool = await asyncpg.connect(**credentials)

	with open('data/schema.sql') as f:
		schema = f.read()

	await pool.execute(schema)

@client.event
async def on_message(message):
	if not is_shout(message.content) or message.author.bot:
		return

	shout = await get_shout()
	if shout: await message.channel.send(shout)
	await save_shout(message)

@client.event
async def on_raw_message_edit(payload):
	if 'webhook_id' in payload.data or 'content' not in payload.data:
		return

	id = payload.message_id
	if not await pool.fetchval('SELECT hash FROM shout WHERE message = $1', id):
		return

	if not is_shout(payload.data['content']):
		await pool.execute('DELETE FROM shout WHERE message = $1', id)
		return

	h = await hash(payload.data['content'])
	try:
		await pool.execute('UPDATE shout SET hash = $1 WHERE message = $2', h, id)
	except asyncpg.UniqueConstraintViolationError:
		# don't store duplicate hashes
		await pool.execute('DELETE FROM shout WHERE message = $1', id)

async def delete_shout(message_id):
	await pool.execute('DELETE FROM shout WHERE message = $1', message_id)

@client.event
async def on_raw_message_delete(payload):
	await delete_shout(payload.message_id)

@client.event
async def on_raw_bulk_message_delete(payload):
	for id in payload.message_ids:
		await delete_shout(id)

async def hash(string):
	return await client.loop.run_in_executor(None, hasher.hash, string)

async def save_shout(message):
	h = await hash(message.content)
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
	except discord.HTTPException:
		return

	return message.content

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


if __name__ == '__main__':
	import os

	client.run(os.environ['LOUDBOT_TOKEN'])
