{
	# obtained from https://my.telegram.org
	'api_id': ...,
	'api_hash': ...,
	# obtained from the BotFather
	'api_token': ...,
	# pick anything?
	'session_name': 'anon',

	# postgresql connection credentials
	# See the parameters list at https://magicstack.github.io/asyncpg/current/api/index.html#connection
	# for a list of possible values.
	'database': {
		'database': 'cc_telegram',
	},

	# @mention of this bot's admin
	'owner': ...,
	# set of user IDs that can run administrative commands on the bot
	'owner_ids': {
	},
}
