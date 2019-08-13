# Copyright © 2018–2019 lambda#0987
#
# CAPTAIN CAPSLOCK is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# CAPTAIN CAPSLOCK is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with CAPTAIN CAPSLOCK.  If not, see <https://www.gnu.org/licenses/>.

import contextlib

import discord.utils
from discord.ext import commands

class Meta(commands.Cog):
	"""Commands pertaining to the bot itself."""

	@commands.command()
	async def invite(self, context):
		"""Gives you a link to add me to your server."""
		await context.send('<%s>' % discord.utils.oauth_url(context.bot.config['client_id']))

	@commands.command()
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
