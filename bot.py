#!/usr/bin/env python3

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

import asyncio
import logging
from functools import wraps

import asyncpg
from telethon import TelegramClient, events, tl

import utils.shout
from db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bot')

def is_command(event):
	# this is insanely complicated kill me now
	message = event.message
	username = getattr(event.client.user, 'username', None)
	if not username:
		logger.warning('I have no username!')
		return False
	dm = isinstance(message.to_id, tl.types.PeerUser)
	for entity, text in message.get_entities_text(tl.types.MessageEntityBotCommand):
		if entity.offset != 0:
			continue
		if dm or text.endswith('@' + username):
			return True
	return False

def command_required(f):
	@wraps(f)
	async def handler(event):
		if not is_command(event):
			return
		return await f(event)
	return handler

@events.register(events.NewMessage)
async def on_message(event):
	message = event.message
	if isinstance(message.to_id, tl.types.PeerUser):
		# don't respond in DMs
		return
	if is_command(event):
		return

	chat_id, user_id = message.to_id.chat_id, message.from_id
	if not utils.shout.is_shout(message.raw_text):  # ignore formatting
		return

	shout = await event.client.db.random_shout(chat_id)
	if shout: await event.respond(shout)
	await event.client.db.save_shout(chat_id, message.id, message.text)  # but replay formatting next time it's said

	raise events.StopPropagation  # not a command, so don't let the command handlers get to it

@events.register(events.NewMessage(pattern=r'^/ping'))
@command_required
async def ping_command(event):
	await event.respond('PONG')

@events.register(events.NewMessage(pattern=r'^/license'))
@command_required
async def license_command(event):
	with open('short-license.txt') as f:
		await event.respond(f.read())

async def main():
	with open('config.py') as f:
		config = eval(f.read(), {})

	client = TelegramClient(config['session_name'], config['api_id'], config['api_hash'])
	client.config = config
	client.pool = await asyncpg.create_pool(**config['database'])
	client.db = Database(client.pool)

	for obj in globals().values():
		if events.is_handler(obj):
			client.add_event_handler(obj)

	await client.start(bot_token=config['api_token'])
	client.user = await client.get_me()

	try:
		await client._run_until_disconnected()
	finally:
		client.disconnect()

if __name__ == '__main__':
	asyncio.get_event_loop().run_until_complete(main())
