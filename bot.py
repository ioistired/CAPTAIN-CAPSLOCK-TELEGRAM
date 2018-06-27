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

	shout = await get_random_shout()
	if shout: await message.channel.send(shout)
	await save_shout(message)

@client.event
async def on_raw_message_edit(payload):
	if 'webhook_id' in payload.data or 'content' not in payload.data:
		return

	id = payload.message_id
	if not await pool.fetchval('SELECT 1 FROM shout WHERE id = $1', id):
		return

	content = payload.data['content']
	if not is_shout(content):
		# don't let people sneakily insert non-shouts into the database
		await delete_shout(id)
		return

	content = sanitize(content)
	try:
		await pool.execute('UPDATE shout SET content = $1 WHERE id = $2', content, id)
	except asyncpg.UniqueViolationError:
		# don't store duplicate shouts
		await pool.execute('DELETE FROM shout WHERE id = $1', id)

@client.event
async def on_raw_message_delete(payload):
	await delete_shout(payload.message_id)

@client.event
async def on_raw_bulk_message_delete(payload):
	for id in payload.message_ids:
		await delete_shout(id)

## DATABASE

async def save_shout(message):
	await pool.execute("""
		INSERT INTO shout(id, content)
		VALUES($1, $2)
		ON CONFLICT DO NOTHING
	""", message.id, sanitize(message.content))

async def get_random_shout():
	return await pool.fetchval("""
		SELECT content
		FROM shout
		ORDER BY random()
		LIMIT 1
	""")

async def get_shout(message_id):
	return await pool.fetchval('SELECT content FROM shout WHERE id = $1', message_id)

async def delete_shout(message_id):
	await pool.execute('DELETE FROM shout WHERE id = $1', message_id)

## MISC

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
