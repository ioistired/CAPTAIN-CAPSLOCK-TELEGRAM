#!/usr/bin/env python3
# encoding: utf-8

import contextlib

import discord.utils
from discord.ext.commands import command

class Meta:
	"""Commands pertaining to the bot itself."""

	@command()
	async def invite(self, context):
		"""Gives you a link to add me to your server."""
		await context.send('<%s>' % discord.utils.oauth_url(context.bot.config['client_id']))

	@command()
	async def support(self, context):
		"""Directs you to the support server."""
		try:
			await context.author.send('https://discord.gg/' + context.bot.config['support_server_invite_code'])
		except discord.HTTPException:
			with contextlib.suppress(discord.HTTPException):
				await context.message.add_reaction(context.bot.config['success_or_failure_emojis'][False])
				await context.send('Unable to send invite in DMs. Please allow DMs from server members.')
		else:
			with contextlib.suppress(discord.HTTPException):
				await context.message.add_reaction('📬')

def setup(bot):
	bot.add_cog(Meta())
	if not bot.config.get('support_server_invite_code'):
		bot.remove_command('support')
