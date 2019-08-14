# CAPTAIN CAPSLOCK

A Discord bot that shouts at you when you shout at it.

## How does it operate?

Say something. Say anything. But say it LOUDLY. The cap' will log what you say (for your server only) and
shout something random back at you. The more you shout at it, the bigger its repertoire gets.
Duplicate text will not be logged.

## What's in a shout?

*Would a scream by any other name still be as loud?*

The algorithm for determining shouts is in [utils/shout.py](https://github.com/bmintz/CAPTAIN-CAPSLOCK/blob/master/utils/shout.py).
It is roughly as follows:

- A sentence is a shout if at least 50% of the words are shouting words (excluding words <3 characters in length)
- A word is a shouting word if >50% of its characters are uppercase.

For example, "you went to college to be a WELL EDUCATED CITIZEN OF THE WORLD, nick" is a shout because more than
half of the words >2 characters long are shouting words ("WELL", "EDUCATED", "CITIZEN", "THE", and "WORLD").

## What commands does it have?

Not many.

- @CAPTAIN CAPSLOCK toggle will enable or disable the shout response and logging for you.
- If you have the Manage Messages permission *server-wide* then you can use the @CAPTAIN CAPSLOCK toggleserver
  command. This will make the shouting auto response opt-in or opt-out for the entire server. If it is opt-in,
  users will need to run @CAPTAIN CAPSLOCK toggle before the bot will log their shouts and repeat them.

## What about message deletes/edits?

Deleting a message will delete its correspond entry in the database, if there is one.
Editing a message will do the same, however, if you sneakily edit a shout so that it's no longer a shout, the bot
will delete the correspond entry in the database.
For example, saying "YOOOOO" and then editing it to "yo" will mean that the cap' will not say "YOOOOO" anymore.

If a channel is deleted, all of its corresponding messages are deleted from the database.

When Captain Caps is kicked from a server, all shouts for that server are deleted from its database.

## How do I run this?

You'll need PostgreSQL 11+ and python3.6+.

```
$ createdb captain_capslock
$ psql captain_capslock -f schema.sql
$ cp data/config.example.json data/config.json
$ # edit config.json as needed
$ python3 -m venv .venv
$ source .venv/bin/activate
$ ./bot.py
```

## License

Copyright © 2018–2019 lambda#0987

CAPTAIN CAPSLOCK is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

CAPTAIN CAPSLOCK is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with CAPTAIN CAPSLOCK.  If not, see <https://www.gnu.org/licenses/>.
