#!/usr/bin/env python3
# encoding: utf-8

import re

import asyncpg
from discord.ext import commands

class Database(commands.Cog):
	def __init__(self, bot):
		self.bot = bot

	async def update_shout(self, message, content):
		content = sanitize(content)
		try:
			await self.bot.pool.execute('UPDATE shout SET content = $1 WHERE message = $2', content, message)
		except asyncpg.UniqueViolationError:
			# don't store duplicate shouts
			await self.bot.pool.execute('DELETE FROM shout WHERE message = $1', message)

	async def save_shout(self, message):
		guild_or_user = get_guild_or_user(message)
		await self.bot.pool.execute("""
			INSERT INTO shout(guild_or_user, message, content)
			VALUES($1, $2, $3)
			ON CONFLICT DO NOTHING
		""", guild_or_user, message.id, sanitize(message.content))

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

		return await self.bot.pool.fetchval(query, *args)

	async def get_shout(self, message_id):
		return await self.bot.pool.fetchval('SELECT content FROM shout WHERE message = $1', message_id)

	async def delete_shout(self, message_id):
		await self.bot.pool.execute('DELETE FROM shout WHERE message = $1', message_id)

	async def delete_shouts(self, message_ids):
		await self.bot.pool.executemany('DELETE FROM shout WHERE message = $1', [(id,) for id in message_ids])

	async def delete_by_guild_or_user(self, guild_or_user):
		await self.bot.pool.execute('DELETE FROM shout WHERE guild_or_user = $1', guild_or_user)

	async def _toggle_state(self, table_name, id, default):
		"""toggle the state for a user or guild. If there's no entry already, new state = default."""
		# see _get_state for why string formatting is OK here
		await self.bot.pool.execute(f"""
			INSERT INTO {table_name} (id, state) VALUES ($1, $2)
			ON CONFLICT (id) DO UPDATE SET state = NOT {table_name}.state
		""", id, default)

	async def toggle_user_state(self, user_id, guild_id=None) -> bool:
		"""Toggle whether the user has opted in to the bot.
		If the user does not have an entry already:
			If the guild_id is provided and not None, the user's state is set to the opposite of the guilds'
			Otherwise, the user's state is set to False (opted out), since the default state is True.
		Returns the new state.
		"""
		default = False
		guild_state = await self.get_guild_state(guild_id)
		if guild_state is not None:
			# if the auto response is enabled for the guild then toggling the user state should opt out
			default = not guild_state
		await self._toggle_state('user_opt', user_id, default)
		return await self.get_user_state(user_id)

	async def toggle_guild_state(self, guild_id):
		"""Togle whether this guild is opt out.
		If this guild is opt in, the shout auto response will be disabled
		except for users that have opted in to it using `toggle_user_state`.
		Otherwise, the response will be on for all users except those that have opted out.
		"""
		await self._toggle_state('guild_opt', guild_id, False)
		return await self.get_guild_state(guild_id)

	async def _get_state(self, table_name, id):
		# unfortunately, using $1 for table_name is a syntax error
		# however, since table name is always hardcoded input from other functions in this module,
		# it's ok to use string formatting here
		return await self.bot.pool.fetchval(f'SELECT state FROM {table_name} WHERE id = $1', id)

	async def get_user_state(self, user_id):
		"""return this user's global preference for the shout auto response and logging"""
		return await self._get_state('user_opt', user_id)

	async def get_guild_state(self, guild_id):
		"""return whether this guild is opt in"""
		return await self._get_state('guild_opt', guild_id)

	async def get_state(self, guild_id, user_id):
		state = True

		guild_state = await self.get_guild_state(guild_id)
		if guild_state is not None:
			state = guild_state

		user_state = await self.get_user_state(user_id)
		if user_state is not None:
			state = user_state  # user state overrides guild state

		return state

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
