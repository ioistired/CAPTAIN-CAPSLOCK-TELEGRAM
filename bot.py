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

import logging
import re

import asyncpg
import discord
from bot_bin.bot import Bot
from discord.ext import commands

logging.basicConfig(level=logging.INFO)
logging.getLogger('discord').setLevel(logging.WARNING)
logger = logging.getLogger('bot')

class CaptainCapslock(Bot):
	def __init__(self, config, **kwargs):
		super().__init__(
			config=config,
			setup_db=True,
			help_command=CapsHelpCommand(),
			case_insensitive=True,
			**kwargs)

	def initial_activity(self):
		return discord.Activity(type=discord.ActivityType.watching, name='YOU SCREAM')

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
		elif (
			isinstance(error, commands.CommandInvokeError)
			and
				getattr(
					type(context.cog),
					'cog_command_error',
					# treat ones with no cog (e.g. eval'd ones) as being in a cog that did not override
					commands.Cog.cog_command_error)
				is commands.Cog.cog_command_error
		):
			await context.send('AN INTERNAL ERROR OCCURED WHILE TRYING TO RUN THAT COMMAND.')
			logger.error('In %s:', context.command.qualified_name)
			logger.error(''.join(traceback.format_tb(error.original.__traceback__)))
			# pylint: disable=logging-format-interpolation
			logger.error('{0.__class__.__name__}: {0}'.format(error.original))

	startup_extensions = (
		'extensions.db',
		'extensions.shout',
		'extensions.meta',
		'bot_bin.misc',
		'bot_bin.stats',
		'bot_bin.sql',
		'jishaku',
	)

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

def load_json_compat(filename):
	with open(filename) as f:
		return eval(f.read(), dict(null=None, false=False, true=True))

if __name__ == '__main__':
	CaptainCapslock(load_json_compat('data/config.py')).run()
