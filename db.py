# Copyright © 2018–2020 Io Mintz <io@mintz.cc>
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

from typing import Type, Union

import asyncpg
import jinja2
from telethon.tl import types
from telethon.extensions import BinaryReader

import utils

PeerType = Union[Type[types.PeerUser], Type[types.PeerChannel], Type[types.PeerChat]]

class Database:
	def __init__(self, pool):
		self.pool = pool
		with open('queries.sql') as f:
			self.queries = jinja2.Template(f.read(), line_statement_prefix='-- :').module

	async def update_shout(self, chat_id, message_id, content):
		async with self.pool.acquire() as conn, conn.transaction():
			try:
				await conn.execute(self.queries.update_shout(), chat_id, message_id, content)
			except asyncpg.UniqueViolationError:
				# don't store duplicate shouts
				await self.delete_shout(chat_id, message_id, connection=conn)

	async def save_shout(self, message):
		# sanitize message content
		content = message.message.replace('@', '@\N{invisible separator}')
		ixs = []
		entities = message.entities or []
		for i, entity in enumerate(entities):
			if isinstance(entity, (types.MessageEntityMention, types.MessageEntityMentionName)):
				ixs.append(i)
		for i in reversed(ixs):
			del entities[i]

		tag = await self.pool.execute(
			self.queries.save_shout(),
			utils.peer_id(message.to_id), message.id, content, list(map(bytes, entities)),
		)
		return tag == 'INSERT 0 1'

	async def random_shout(self, peer):
		chat_id = utils.peer_id(peer)
		row = await self.pool.fetchrow(self.queries.random_shout(), chat_id)
		if row is None:
			return None
		message_id, content, encoded_entities = row
		entities = [BinaryReader(encoded).tgread_object() for encoded in encoded_entities]
		return types.Message(id=message_id, to_id=chat_id, message=content, entities=entities)

	async def delete_shout(self, chat_id, message_id, *, connection=None):
		tag = await (connection or self.pool).execute(self.queries.delete_shout(), chat_id, message_id)
		return int(tag.split()[-1])

	async def delete_by_chat(self, chat_id):
		tag = await self.pool.execute(self.queries.delete_by_chat(), guild_or_user)
		return int(tag.split()[-1])

	async def state_for(self, peer_type: PeerType, id):
		return await self.pool.fetchval(self.queries.state_for(), peer_type.__name__, id)

	async def toggle_state(self, peer_type: PeerType, id, *, default_new_state=False):
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
		default_new_state = False
		chat_state = await self.state_for(types.PeerChat, chat_id) if chat_id is not None else default_new_state
		if chat_state is not None:
			# if the auto response is enabled for the chat then toggling the user state should opt out
			default_new_state = not chat_state
		return await self.toggle_state(types.PeerUser, user_id, default_new_state=default_new_state)

	async def state(self, peer_type, peer_id, user_id):
		return await self.pool.fetchval(self.queries.state(), peer_type.__name__, peer_id, user_id)
