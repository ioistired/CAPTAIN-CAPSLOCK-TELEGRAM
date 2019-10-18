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
import contextlib
import logging
from functools import wraps

import asyncpg
from telethon import TelegramClient, errors, events, tl

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
		await f(event)
		raise events.StopPropagation
	return handler

def group_required(f):
	@wraps(f)
	async def handler(event):
		if not isinstance(event.message.to_id, tl.types.PeerChat):
			await event.respond('THIS COMMAND MAY NOT BE USED IN PRIVATE MESSAGES')
		else:
			return await f(event)
	return handler

# so that we can register them all in the correct order later (globals() is not guaranteed to be ordered)
event_handlers = []
def register_event(*args, **kwargs):
	def deco(f):
		event_handlers.append(events.register(*args, **kwargs)(f))
		return f
	return deco

@register_event(events.NewMessage)
async def on_message(event):
	message = event.message
	if is_command(event):
		return

	if not utils.shout.is_shout(message.raw_text):  # ignore formatting
		raise events.StopPropagation  # not a command, so don't let the command handlers get to it

	if isinstance(message.to_id, tl.types.PeerUser):
		# this bot doesn't work in DMs but that doesn't mean we can't have a bit of fun
		await event.respond('KEEP YOUR VOICE DOWN')
		raise events.StopPropagation

	chat_id, user_id = message.to_id.chat_id, message.from_id
	if not await event.client.db.state(chat_id, user_id):
		return

	shout = await event.client.db.random_shout(chat_id)
	if shout: await event.respond(shout)
	await event.client.db.save_shout(chat_id, message.id, message.text)  # but replay formatting next time it's said

	raise events.StopPropagation

@register_event(events.NewMessage(pattern=r'^/ping'))
@command_required
async def ping_command(event):
	await event.respond('PONG')

@register_event(events.NewMessage(pattern=r'^/license'))
@command_required
async def license_command(event):
	with open('short-license.txt') as f:
		await event.respond(f.read())

@register_event(events.NewMessage(pattern=r'^/togglegroup'))
@group_required
@command_required
async def togglegroup_command(event):
	message = event.message
	new_state = await event.client.db.toggle_state(type(event.message.to_id), event.message.to_id.chat_id)
	if new_state:
		await event.respond('SHOUTING AUTO RESPONSE IS NOW **OPT-OUT** FOR THIS CHAT')
	else:
		await event.respond('SHOUTING AUTO RESPONSE IS NOW **OPT-IN** FOR THIS CHAT')

@register_event(events.NewMessage(pattern=r'^/toggle'))
@command_required
async def toggle_command(event):
	message = event.message
	chat_id = message.to_id.chat_id if isinstance(message.to_id, tl.types.PeerChat) else None
	new_state = await event.client.db.toggle_user_state(event.message.from_id, chat_id)
	if new_state:
		await event.respond('OPTED IN TO THE SHOUTING AUTO RESPONSE')
	else:
		await event.respond('OPTED OUT OF THE SHOUTING AUTO RESPONSE')

@register_event(events.NewMessage(pattern=r'^/remove'))
@group_required
@command_required
async def remove_command(event):
	message = event.message

	if message.reply_to_msg_id is None:
		await event.respond(
			"HOW AM I SUPPOSED TO REMOVE A MESSAGE FROM MY DATABASE IF YOU WON'T TELL ME WHICH ONE TO REMOVE?")
		return

	if event.is_group and event.is_channel:
		logging.info('%s tried to run /remove in a megagroup', (await event.get_sender()).username)
		await event.respond(f'THIS COMMAND DOES NOT SUPPORT MEGA GROUPS YET. PLEASE CONTACT {event.client.config["owner"]}.')
		return

	# we're not in a mega group. members of small groups can delete any message, so they have permission to run this command.

	to_delete = []
	if await event.client.db.delete_shout(message.to_id.chat_id, message.reply_to_msg_id):
		to_delete.append(await event.respond('DELETED'))
	else:
		to_delete.append(await event.respond('MESSAGE NOT FOUND IN MY DATABASE'))
	to_delete.append(event.message)  # this comes last because it's more likely to fail

	await asyncio.sleep(3)
	with contextlib.suppress(errors.MessageDeleteForbiddenError):
		# we don't use client.delete_messages because that errors if *any* message fails to delete
		for msg in to_delete:
			await msg.delete()

async def main():
	with open('config.py') as f:
		config = eval(f.read(), {})

	client = TelegramClient(config['session_name'], config['api_id'], config['api_hash'])
	client.config = config
	client.pool = await asyncpg.create_pool(**config['database'])
	client.db = Database(client.pool)

	for handler in event_handlers:
		client.add_event_handler(handler)

	await client.start(bot_token=config['api_token'])
	client.user = await client.get_me()

	try:
		await client._run_until_disconnected()
	finally:
		client.disconnect()

if __name__ == '__main__':
	asyncio.get_event_loop().run_until_complete(main())
