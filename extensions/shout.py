#!/usr/bin/env python3
# encoding: utf-8

from is_shout import is_shout

class Shout:
	def __init__(self, bot):
		self.bot = bot
		self.db = self.bot.get_cog('Database')

	async def on_message(self, message):
		if not is_shout(message.content) or message.author.bot:
			return

		shout = await self.db.get_random_shout(message)
		if shout: await message.channel.send(shout)
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
