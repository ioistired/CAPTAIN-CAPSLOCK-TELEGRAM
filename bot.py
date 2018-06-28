#!/usr/bin/env python3
# encoding: utf-8

import logging
import json

from discord.ext import commands

logging.basicConfig()
logger = logging.getLogger('bot')
logger.setLevel(logging.INFO)

class Loudbot(commands.AutoShardedBot):
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


if __name__ == '__main__':
	Loudbot().run()

