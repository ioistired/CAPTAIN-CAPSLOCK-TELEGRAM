#!/usr/bin/env python3

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

import asyncio
import contextlib
import logging
from random import random
from functools import wraps

import asyncpg
import telethon
from telethon import TelegramClient, errors, events, tl
from jishaku.repl import AsyncCodeExecutor
from jishaku.functools import AsyncSender

import utils
from db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bot')

def is_command(event):
	# this is insanely complicated kill me now
	message = event.message
	try:
		me = event.client.user
		username = me.username
	except AttributeError:
		logger.warning('Command ran before event.client was set up!')
		return False

	if message.from_id == me.id:
		return False

	dm = isinstance(message.to_id, tl.types.PeerUser)
	for entity, text in message.get_entities_text(tl.types.MessageEntityBotCommand):
		if entity.offset != 0:
			break
		if dm or text.endswith('@' + username):
			event.command_text = event.message.raw_text[len(text):].strip()
			return True
	return False

def check(predicate):
	predicate = utils.ensure_corofunc(predicate)
	def deco(wrapped_handler):
		@wraps(wrapped_handler)
		async def handler(event):
			if await predicate(event):
				await wrapped_handler(event)
		return handler
	return deco

command_required = check(is_command)

@check
def owner_required(event):
	return event.sender.id in event.client.config['owner_ids']

@check
async def group_required(event):
	if isinstance(event.message.to_id, tl.types.PeerUser):
		await event.respond('THIS COMMAND MUST BE USED IN A GROUP CHAT')
		raise events.StopPropagation
	return True

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

	if message.from_id == event.client.user.id:
		return

	# ignore formatting, and don't consider code to be a shout
	# (SQL LIKES TO YELL)
	if not utils.shout.is_shout(utils.remove_code_and_mentions(message)):
		return

	if isinstance(message.to_id, tl.types.PeerUser):
		# this bot doesn't work in DMs but that doesn't mean we can't have a bit of fun
		await event.respond('KEEP YOUR VOICE DOWN')
		raise events.StopPropagation

	peer_id, user_id = event.chat_id, message.from_id
	if not await event.client.db.state(peer_id, user_id):
		return

	# try to reduce spam
	if random() < 0.6:
		shout = await event.client.db.random_shout(message.to_id)
		await event.respond(shout or "I AIN'T GOT NOTHIN' ON THAT")

	await event.client.db.save_shout(message)
	raise events.StopPropagation

@register_event(events.NewMessage(pattern=r'^/ping'))
@command_required
async def ping_command(event):
	await event.respond('PONG')

@register_event(events.NewMessage(pattern=r'^/license'))
@command_required
async def license_command(event):
	with open('short-license.txt') as f:
		await event.respond(f.read(), parse_mode='markdown')

@register_event(events.NewMessage(pattern=r'^/togglegroup'))
@group_required
@command_required
async def togglegroup_command(event):
	message = event.message
	new_state = await event.client.db.toggle_state(event.chat_id)
	if new_state:
		await event.respond('SHOUTING AUTO RESPONSE IS NOW **OPT-OUT** FOR THIS CHAT', parse_mode='markdown')
	else:
		await event.respond('SHOUTING AUTO RESPONSE IS NOW **OPT-IN** FOR THIS CHAT', parse_mode='markdown')

	# don't invoke /toggle as well
	raise events.StopPropagation

@register_event(events.NewMessage(pattern=r'^/toggle'))
@command_required
async def toggle_command(event):
	message = event.message
	chat_id = event.chat_id if not isinstance(message.to_id, tl.types.PeerUser) else None
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
		participant = await event.client(tl.functions.channels.GetParticipantRequest(
			channel=message.to_id,
			user_id=message.from_id))
		if not (isinstance(participant, tl.types.ChannelParticipantAdmin) and participant.admin_rights.delete_messages):
			await event.respond('YOU MUST BE AN ADMIN WITH DELETE MESSAGES PERMISSION TO RUN THIS COMMAND.')
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

@register_event(events.NewMessage(pattern=r'^/py'))
@command_required
@owner_required
async def python(event):
	message = event.message
	async with utils.ReplExceptionCatcher(message):
		async for send, x in AsyncSender(AsyncCodeExecutor(event.command_text, arg_dict=dict(
			event=event,
			telethon=telethon,
			tl=tl,
			message=message,
			_=event.client.last_python_result,
		))):
			if x is not None:
				event.client.last_python_result = x

			if not isinstance(x, str):
				x = repr(x)

			if not x.strip():
				# represent nothingness, without actually sending nothing
				x = '\N{zero width space}'

			message = await message.reply(x)
			send(message)

		await event.reply('✅')

async def init_client():
	import ast
	with open('config.py') as f:
		config = ast.literal_eval(f.read())

	client = TelegramClient(config['session_name'], config['api_id'], config['api_hash'])
	client.parse_mode = None  # disable markdown parsing
	client.config = config
	pool = await asyncpg.create_pool(**config['database'])
	client.db = Database(pool)
	client.last_python_result = None

	for handler in event_handlers:
		client.add_event_handler(handler)

	return client

async def main():
	client = await init_client()
	await client.start(bot_token=client.config['api_token'])
	client.user = await client.get_me()

	await client.run_until_disconnected()

if __name__ == '__main__':
	with contextlib.suppress(KeyboardInterrupt):
		asyncio.get_event_loop().run_until_complete(main())
