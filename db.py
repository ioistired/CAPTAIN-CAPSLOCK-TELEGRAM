# Copyright © 2018–2019 Io Mintz <io@mintz.cc>
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

import typing

import asyncpg
import jinja2
from telethon.tl import types

PeerType = typing.Union[typing.Type[types.PeerUser], typing.Type[types.PeerChannel], typing.Type[types.PeerChat]]

class Database:
	def __init__(self, pool):
		self.pool = pool
		with open('queries.sql') as f:
			self.queries = jinja2.Template(f.read(), line_statement_prefix='-- :').module

	async def update_shout(self, message_id, content):
		async with self.pool.acquire() as conn, conn.transaction():
			try:
				await conn.execute(self.queries.update_shout(), message_id, content)
			except asyncpg.UniqueViolationError:
				# don't store duplicate shouts
				await self.delete_shout(message_id, connection=conn)

	async def save_shout(self, chat_id, message_id, content):
		tag = await self.pool.execute(self.queries.save_shout(), chat_id, message_id, content)
		return tag == 'INSERT 0 1'

	async def random_shout(self, chat_id):
		return await self.pool.fetchval(self.queries.random_shout(), chat_id)

	async def delete_shout(self, message_id, *, connection=None):
		tag = await (connection or self.pool).execute(self.queries.delete_shout(), message_id)
		return int(tag.split()[-1])

	async def delete_by_chat(self, chat_id):
		tag = await self.pool.execute(self.queries.delete_by_chat(), guild_or_user)
		return int(tag.split()[-1])

	async def state_for(self, peer_type: PeerType, id):
		return await self.pool.fetchval(self.queries.state_for(), peer_type.__name__, id)

	async def toggle_state(self, peer_type: PeerType, id, default_new_state):
		"""toggle the state for a user or guild. If there's no entry already, new state = default_new_state."""
		return await self.pool.fetchval(self.queries.toggle_state(), peer_type.__name__, id, default_new_state)

	async def set_state(self, peer_type: PeerType, id, new_state):
		await self.pool.execute(self.queries.set_state(), peer_type.__name__, guild_id, new_state)

	async def toggle_user_state(self, user_id, chat_id=None) -> bool:
		"""Toggle whether the user has opted in to the bot.
		If the user does not have an entry already:
			If the chat_id is provided and not None, the user's state is set to the opposite of the chat'
			Otherwise, the user's state is set to True (opted in), since the default state is False.
		Returns the new state.
		"""
		default_new_state = True
		chat_state = await self.state_for(types.PeerChat, chat_id) if chat_id is not None else default_new_state
		if chat_state is not None:
			# if the auto response is enabled for the chat then toggling the user state should opt out
			default_new_state = not chat_state
		return await self.toggle_state(types.PeerUser, user_id, default_new_state)

	async def state(self, chat_id, user_id):
		return await self.bot.pool.fetchval(self.queries.get_state(), chat_id, user_id)
