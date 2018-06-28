#!/usr/bin/env python3
# encoding: utf-8

import asyncio
import json
import re
import sys

import asyncpg
import discord

from is_shout import is_shout

client = discord.AutoShardedClient()

## EVENTS

@client.event
async def on_ready():
	await load_db()
	print('Ready')

@client.event
async def on_message(message):
	if not is_shout(message.content) or message.author.bot:
		return

	shout = await get_random_shout(get_guild_or_user(message))
	if shout: await message.channel.send(shout)
	await save_shout(message)

@client.event
async def on_raw_message_edit(payload):
	if 'webhook_id' in payload.data or 'content' not in payload.data:
		return

	id = payload.message_id
	content = payload.data['content']
	if not is_shout(content):
		# don't let people sneakily insert non-shouts into the database
		await delete_shout(id)
		return

	content = sanitize(content)
	try:
		await pool.execute('UPDATE shout SET content = $1 WHERE message = $2', content, id)
	except asyncpg.UniqueViolationError:
		# don't store duplicate shouts
		await pool.execute('DELETE FROM shout WHERE message = $1', id)

@client.event
async def on_raw_message_delete(payload):
	await delete_shout(payload.message_id)

@client.event
async def on_raw_bulk_message_delete(payload):
	for id in payload.message_ids:
		await delete_shout(id)

@client.event
async def on_guild_remove(guild):
	await pool.execute('DELETE FROM shout WHERE guild_or_user = $1', guild.id)

## DATABASE

async def save_shout(message):
	guild_or_user = get_guild_or_user(message)
	await pool.execute("""
		INSERT INTO shout(guild_or_user, message, content)
		VALUES($1, $2, $3)
		ON CONFLICT DO NOTHING
	""", guild_or_user, message.id, sanitize(message.content))

async def get_random_shout(guild_or_user=None):
	args = []
	query = """
		SELECT content
		FROM shout
	"""

	if guild_or_user is not None:
		query += 'WHERE guild_or_user = $1'
		args.append(guild_or_user)

	query += """
		ORDER BY random()
		LIMIT 1
	"""

	return await pool.fetchval(query, *args)

async def get_shout(message_id):
	return await pool.fetchval('SELECT content FROM shout WHERE message = $1', message_id)

async def delete_shout(message_id):
	await pool.execute('DELETE FROM shout WHERE message = $1', message_id)

## MISC

def get_guild_or_user(message):
	try:
		return message.channel.guild.id
	except AttributeError:
		return message.author.id

def sanitize(s):
	s = re.sub(r'<@!?\d+>', '@SOMEONE', s, re.ASCII)
	s = re.sub(r'<@&\d+>',  '@SOME ROLE', s, re.ASCII)
	s = s.replace('@everyone', '@EVERYONE')
	s = s.replace('@here', f'@HERE')

	return s

async def load_db():
	global pool

	credentials = config['database']

	try:
		pool = await asyncpg.create_pool(credentials['url'])
	except KeyError:
		pool = await asyncpg.create_pool(**credentials)

	with open('schema.sql') as f:
		schema = f.read()

	await pool.execute(schema)

with open('data/config.json') as f:
	config = json.load(f)
del f

if __name__ == '__main__':
	client.run(config['tokens']['discord'])
