#!/usr/bin/env python3
# encoding: utf-8

import discord.utils
from discord.ext.commands import command
command = command()

class Meta:
	"""Commands pertaining to the bot itself."""

	def __init__(self, bot):
		self.bot = bot

	@command
	async def invite(self, context):
		"""Gives you a link to add me to your server."""
		await context.send('<%s>' % discord.utils.oauth_url(self.bot.config['client_id']))

def setup(bot):
	bot.add_cog(Meta(bot))
