#!/usr/bin/env python3

# Copyright © 2018–2019 lambda#0987
#
# CAPTAIN CAPSLOCK is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CAPTAIN CAPSLOCK is distributed in the hope that it will be fun,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with CAPTAIN CAPSLOCK.  If not, see <https://www.gnu.org/licenses/>.

import contextlib
import logging
import json
import re
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

	async def login(self, token=None, **kwargs):
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
		try:
			await super().close()
		finally:
			with contextlib.suppress(AttributeError):
				await self.pool.close()

	# Using code provided by Rapptz under the MIT License
	# Copyright © 2015–2019 Rapptz
	# https://github.com/Rapptz/discord.py/blob/v1.2.3/discord/ext/commands/converter.py#L459-L530
	def clean_content(
		self,
		*,
		guild,
		content,
		fix_channel_mentions=False,
		use_nicknames=True,
		escape_markdown=False,
	):
		transformations = {}

		if fix_channel_mentions and guild:
			def resolve_channel(id, *, _get=message.guild.get_channel):
				ch = _get(id)
				return ('<#%s>' % id), ('#' + ch.name if ch else '#deleted-channel')

			transformations.update(resolve_channel(int(channel)) for channel in re.findall(r'<#([0-9]+)>', content))

		if use_nicknames and guild:
			def resolve_member(id, *, _get=guild.get_member):
				m = _get(id)
				return '@' + m.display_name if m else '@deleted-user'
		else:
			def resolve_member(id, *, _get=self.get_user):
				m = _get(id)
				return '@' + m.name if m else '@deleted-user'

		raw_mentions = [int(x) for x in re.findall(r'<@!?([0-9]+)>', content)]

		transformations.update(
			('<@%s>' % member_id, resolve_member(member_id))
			for member_id in raw_mentions
		)

		transformations.update(
			('<@!%s>' % member_id, resolve_member(member_id))
			for member_id in raw_mentions
		)

		if guild:
			def resolve_role(id):
				r = guild.get_role(id)
				return '@' + r.name if r else '@deleted-role'

			transformations.update(
				('<@&%s>' % role_id, resolve_role(int(role_id)))
				for role_id in re.findall(r'<@&([0-9]+)>', content)
			)

		def repl(match):
			return transformations.get(match[0], '')

		pattern = re.compile('|'.join(transformations.keys()))
		result = pattern.sub(repl, content)

		if escape_markdown:
			result = discord.utils.escape_mentions(result)

		# Completely ensure no mentions escape:
		return discord.utils.escape_mentions(result)

class CapsHelpCommand(commands.MinimalHelpCommand):
	async def send_pages(self):
		destination = self.get_destination()
		for page in self.paginator.pages:
			await destination.send(page.upper())

if __name__ == '__main__':
	with open('data/config.json') as f:
		config = json.load(f)

	CaptainCapslock(config).run()
