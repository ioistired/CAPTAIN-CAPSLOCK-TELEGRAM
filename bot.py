#!/usr/bin/env python3
# encoding: utf-8

import logging
import json
import traceback

from discord.ext import commands

logging.basicConfig(level=logging.WARN)
logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)

class CaptainCapslock(commands.AutoShardedBot):
	def __init__(self, *args, **kwargs):
		with open('data/config.json') as f:
			self.config = json.load(f)

		super().__init__(*args, command_prefix=commands.when_mentioned, **kwargs)

	def run(self):
		for extension in self.config['startup_extensions']:
			self.load_extension(extension)
			logger.info('loaded extension %s successfully', extension)
		super().run(self.config['tokens']['discord'])

	async def on_ready(self):
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

		if not self.config.get('ignore_bots'):
			return False

		should_reply = not self.config['ignore_bots'].get('default')
		overrides = self.config['ignore_bots']['overrides']

		def check_override(location, overrides_key):
			if not isinstance(overrides[overrides_key], frozenset):
				# make future lookups faster
				overrides[overrides_key] = frozenset(overrides[overrides_key])
			return location and location.id in overrides[overrides_key]

		if check_override(message.guild, 'guilds') or check_override(message.channel, 'channels'):
			should_reply = not should_reply

		return should_reply

	async def on_command_error(self, context, error):
		if isinstance(error, commands.NoPrivateMessage):
			await context.author.send('This command cannot be used in private messages.')
		elif isinstance(error, commands.DisabledCommand):
			message = 'Sorry. This command is disabled and cannot be used.'
			try:
				await context.author.send(message)
			except discord.Forbidden:
				await context.send(message)
		elif isinstance(error, commands.UserInputError):
			await context.send(error)
		elif isinstance(error, commands.NotOwner):
			logger.error('%s tried to run %s but is not the owner', context.author, context.command.name)
		elif isinstance(error, commands.CommandInvokeError):
			await context.send('An internal error occured while trying to run that command.')
			logger.error('In %s:', context.command.qualified_name)
			logger.error(''.join(traceback.format_tb(error.original.__traceback__)))
			# pylint: disable=logging-format-interpolation
			logger.error('{0.__class__.__name__}: {0}'.format(error.original))


if __name__ == '__main__':
	CaptainCapslock().run()
