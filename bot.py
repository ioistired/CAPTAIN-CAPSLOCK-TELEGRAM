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
