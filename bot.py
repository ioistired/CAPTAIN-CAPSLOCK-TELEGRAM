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
import re

import asyncpg
from telethon import TelegramClient, events, tl

import utils.shout
from db import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('bot')

with open('config.py') as f:
	config = eval(f.read(), {})

bot = TelegramClient('test', config['api_id'], config['api_hash'])

def is_command(message):
	return (message.entities and any(
		isinstance(entity, tl.types.MessageEntityBotCommand) and entity.offset == 0 for entity in message.entities))

@bot.on(events.NewMessage)
async def on_message(event):
	message = event.message
	if isinstance(message.to_id, tl.types.PeerUser):
		# don't respond in DMs
		return

	if is_command(message):
		return

	chat_id, user_id = message.to_id.chat_id, message.from_id
	if not utils.shout.is_shout(message.raw_text):  # ignore formatting
		return

	shout = await bot.db.random_shout(chat_id)
	if shout: await event.respond(shout)
	await bot.db.save_shout(chat_id, message.id, message.text)  # but replay formatting next time it's said

async def main():
	bot.pool = await asyncpg.create_pool(**config['database'])
	bot.db = Database(bot.pool)
	await bot.start(bot_token=config['api_token'])
	await bot._run_until_disconnected()

if __name__ == '__main__':
	asyncio.get_event_loop().run_until_complete(main())
