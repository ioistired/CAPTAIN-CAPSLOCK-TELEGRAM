#!/usr/bin/env python3
# encoding: utf-8

import logging

from discord.ext import commands

from utils.shout import is_shout

logger = logging.getLogger(__name__)

# Used under the MIT license. Copyright (c) 2017 BeatButton
# https://github.com/BeatButton/beattie/blob/44fd795aef7b1c19233510cda8046baab5ecabf3/utils/checks.py
def owner_or_permissions(**perms):
	"""Checks if the member is a bot owner or has any of the permissions necessary."""
	async def predicate(ctx):
		if await ctx.bot.is_owner(ctx.author):
			return True
		permissions = ctx.channel.permissions_for(ctx.author)
		return any(getattr(permissions, perm, None) == value
				   for perm, value in perms.items())
	return commands.check(predicate)

class Shout:
	def __init__(self, bot):
		self.bot = bot
		self.db = self.bot.get_cog('Database')

	@commands.command(aliases=['toggle-user'])
	async def toggle(self, context):
		"""Toggles the shout auto response and logging for you.
		This is global, ie it affects all servers you are in.

		If a server has been set to opt in, you will need to run this command before I can respond to you.
		"""
		guild = None
		if context.guild is not None:
			guild = context.guild.id
		if await self.db.toggle_user_state(context.author.id, guild):
			action = 'in to'
		else:
			action = 'out of'
		await context.send(f'Opted {action} the shout auto response.')

	@commands.command(name='toggleserver', aliases=['toggle-server'])
	@owner_or_permissions(manage_messages=True)
	@commands.guild_only()
	async def toggle_guild(self, context):
		"""Toggle the shouting auto response for this server.
		If you have never run this command before, this server is opt-out: the shout auto response is
		on for all users, except those who run the toggle-user command.

		If this server is opt-out, the emote auto response is off for all users,
		and they must run the toggle-user command before the bot will respond to them.

		Opt in mode is useful for very large servers where the bot's response would be annoying or
		would conflict with that of other bots.
		"""
		if await self.db.toggle_guild_state(context.guild.id):
			new_state = 'opt-out'
		else:
			new_state = 'opt-in'
		await context.send(f'Shout auto response is now {new_state} for this server.')

	async def on_message(self, message):
		if not is_shout(message.content) or not self.bot.should_reply(message):
			return

		context = await self.bot.get_context(message)
		if context.command:
			# don't respond here if the user has sent a command
			return

		if message.guild:
			guild = message.guild.id
		else:
			guild = None

		if not await self.db.get_state(guild, message.author.id):
			return

		shout = await self.db.get_random_shout(message)
		if shout: await message.channel.send(shout)  # := when
		await self.db.save_shout(message)

	async def on_raw_message_edit(self, payload):
		if 'webhook_id' in payload.data or 'content' not in payload.data:
			return

		id = payload.message_id
		content = payload.data['content']
		if not is_shout(content):
			# don't let people sneakily insert non-shouts into the database
			await self.db.delete_shout(id)
			return

		await self.db.update_shout(id, content)

	async def on_raw_message_delete(self, payload):
		await self.db.delete_shout(payload.message_id)

	async def on_raw_bulk_message_delete(self, payload):
		for id in payload.message_ids:
			await self.db.delete_shout(id)

	async def on_guild_remove(self, guild):
		await self.db.delete_by_guild_or_user(guild.id)

def setup(bot):
	bot.add_cog(Shout(bot))
