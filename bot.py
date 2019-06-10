#!/usr/bin/env python3
# encoding: utf-8

import contextlib
import logging
import json
import traceback

import asyncpg
import discord
from discord.ext import commands

logging.basicConfig(level=logging.WARN)
logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)

class CaptainCapslock(commands.AutoShardedBot):
	activity = discord.Activity(type=discord.ActivityType.watching, name='YOU SCREAM')

	def __init__(self, config, *args, **kwargs):
		self.config = config
		self.process_config()

		super().__init__(
			*args,
			activity=self.activity,
			command_prefix=commands.when_mentioned,
			help_command=CapsHelpCommand(),
			case_insensitive=True)

	def process_config(self):
		self.config.setdefault('success_or_failure_emojis', ('❌', '✅'))

		ignore_bots_conf = self.config.setdefault('ignore_bots', {})
		ignore_bots_conf.setdefault('default', True)
		overrides_conf = ignore_bots_conf.setdefault('overrides', {})
		overrides_conf.setdefault('guilds', ())
		overrides_conf.setdefault('channels', ())
		overrides_conf['guilds'] = set(overrides_conf['guilds'])
		overrides_conf['channels'] = set(overrides_conf['channels'])

	async def on_ready(self):
		await self.change_presence(activity=self.activity)
		logger.info('Ready')

	async def on_message(self, message):
		if self.should_reply(message):
			await self.process_commands(message)

	def should_reply(self, message):
		"""return whether the bot should reply to a given message"""
		return not (
			message.author == self.user
			or (message.author.bot and not self._should_reply_to_bot(message))
			or not message.content)

	def _should_reply_to_bot(self, message):
		if message.author == self.user:
			return False

		should_reply = not self.config['ignore_bots']['default']
		overrides = self.config['ignore_bots']['overrides']

		def check_override(location, overrides_key):
			return location and location.id in overrides[overrides_key]

		if check_override(message.guild, 'guilds') or check_override(message.channel, 'channels'):
			should_reply = not should_reply

		return should_reply

	async def login(self, token, *, bot=True):
		token = self.config['tokens'].pop('discord')
		credentials = self.config.pop('database')

		try:
			self.pool = await asyncpg.create_pool(credentials['url'])
		except KeyError:
			self.pool = await asyncpg.create_pool(**credentials)

		await super().login(token, bot=bot)

	async def close(self):
		try:
			await super().close()
		finally:
			with contextlib.suppress(AttributeError):
				await self.pool.close()

	async def on_command_error(self, context, error):
		if isinstance(error, commands.NoPrivateMessage):
			await context.author.send('THIS COMMAND CANNOT BE USED IN PRIVATE MESSAGES.')
		elif isinstance(error, commands.DisabledCommand):
			message = 'SORRY. THIS COMMAND IS DISABLED AND CANNOT BE USED.'
			try:
				await context.author.send(message)
			except discord.Forbidden:
				await context.send(message)
		elif isinstance(error, commands.UserInputError):
			await context.send(str(error).upper())
		elif isinstance(error, commands.NotOwner):
			logger.error('%s tried to run %s but is not the owner', context.author, context.command.name)
		elif isinstance(error, commands.CommandInvokeError):
			await context.send('AN INTERNAL ERROR OCCURED WHILE TRYING TO RUN THAT COMMAND.')
			logger.error('In %s:', context.command.qualified_name)
			logger.error(''.join(traceback.format_tb(error.original.__traceback__)))
			# pylint: disable=logging-format-interpolation
			logger.error('{0.__class__.__name__}: {0}'.format(error.original))

	async def login(self, *args, **kwargs):
		await self._init_db()
		self._load_extensions()
		token = self.config['tokens'].pop('discord')
		await super().login(token, **kwargs)

	async def _init_db(self):
		credentials = self.config.pop('database')

		try:
			self.pool = await asyncpg.create_pool(credentials['url'])
		except KeyError:
			self.pool = await asyncpg.create_pool(**credentials)

	def _load_extensions(self):
		for extension in [
			'extensions.db',
			'extensions.shout',
			'extensions.meta',
			'ben_cogs.misc',
			'ben_cogs.stats',
			'ben_cogs.sql',
			'jishaku'
		]:
			self.load_extension(extension)
			logger.info('loaded extension %s successfully', extension)

	async def close(self):
		with contextlib.suppress(AttributeError):
			await self.pool.close()
		await super().close()


class CapsHelpCommand(commands.MinimalHelpCommand):
	async def send_pages(self):
		destination = self.get_destination()
		for page in self.paginator.pages:
			await destination.send(page.upper())

if __name__ == '__main__':
	with open('data/config.json') as f:
		config = json.load(f)

	CaptainCapslock(config).run()
