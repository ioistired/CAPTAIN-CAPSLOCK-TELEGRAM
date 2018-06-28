#!/usr/bin/env python3
# encoding: utf-8

import asyncio
from functools import wraps
import re

import asyncpg

def wait(func):
	@wraps(func)
	async def wrapped(self, *args, **kwargs):
		await self.ready.wait()
		return await func(self, *args, **kwargs)
	return wrapped

class Database:
	def __init__(self, bot):
		self.bot = bot
		self.ready = asyncio.Event()
		self._init_db_task = self.bot.loop.create_task(self._init_db())

	def __unload(self):
		self._init_db_task.cancel()

		try:
			self.bot.loop.create_task(self._pool.close())
		except AttributeError:
			pass

	@wait
	async def update_shout(self, message, content):
		content = sanitize(content)
		try:
			await self._pool.execute('UPDATE shout SET content = $1 WHERE message = $2', content, message)
		except asyncpg.UniqueViolationError:
			# don't store duplicate shouts
			await self._pool.execute('DELETE FROM shout WHERE message = $1', message)

	@wait
	async def save_shout(self, message):
		guild_or_user = get_guild_or_user(message)
		await self._pool.execute("""
			INSERT INTO shout(guild_or_user, message, content)
			VALUES($1, $2, $3)
			ON CONFLICT DO NOTHING
		""", guild_or_user, message.id, sanitize(message.content))

	@wait
	async def get_random_shout(self, message=None):
		args = []
		query = """
			SELECT content
			FROM shout
		"""

		if message is not None:
			query += 'WHERE guild_or_user = $1'
			args.append(get_guild_or_user(message))

		query += """
			ORDER BY random()
			LIMIT 1
		"""

		return await self._pool.fetchval(query, *args)

	@wait
	async def get_shout(self, message_id):
		return await self._pool.fetchval('SELECT content FROM shout WHERE message = $1', message_id)

	@wait
	async def delete_shout(self, message_id):
		await self._pool.execute('DELETE FROM shout WHERE message = $1', message_id)

	@wait
	async def delete_by_guild_or_user(self, guild_or_user):
		await self._pool.execute('DELETE FROM shout WHERE guild_or_user = $1', guild_or_user)

	async def _init_db(self):
		credentials = self.bot.config['database']

		try:
			pool = await asyncpg.create_pool(credentials['url'])
		except KeyError:
			pool = await asyncpg.create_pool(**credentials)

		with open('schema.sql') as f:
			schema = f.read()

		await pool.execute(schema)
		self._pool = pool
		self.ready.set()

def sanitize(s):
	s = re.sub(r'<@!?\d+>', '@SOMEONE', s, re.ASCII)
	s = re.sub(r'<@&\d+>',  '@SOME ROLE', s, re.ASCII)
	s = s.replace('@everyone', '@EVERYONE')
	s = s.replace('@here', f'@HERE')

	return s

def get_guild_or_user(message):
	try:
		return message.channel.guild.id
	except AttributeError:
		return message.author.id

def setup(bot):
	bot.add_cog(Database(bot))
