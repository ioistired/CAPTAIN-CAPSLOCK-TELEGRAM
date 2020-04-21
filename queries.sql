-- Copyright © 2018–2020 lambda#0987
--
-- CAPTAIN CAPSLOCK is free software: you can redistribute it and/or modify
-- it under the terms of the GNU Affero General Public License as published
-- by the Free Software Foundation, either version 3 of the License, or
-- (at your option) any later version.
--
-- CAPTAIN CAPSLOCK is distributed in the hope that it will be fun,
-- but WITHOUT ANY WARRANTY; without even the implied warranty of
-- MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
-- GNU Affero General Public License for more details.
--
-- You should have received a copy of the GNU Affero General Public License
-- along with CAPTAIN CAPSLOCK.  If not, see <https://www.gnu.org/licenses/>.

-- :macro update_shout()
-- params: chat_id, message_id, content
UPDATE shout
SET content = $3
WHERE (chat_id, message_id) = ($1, $2)
-- :endmacro

-- :macro delete_shout()
-- params: chat_id, message_id
DELETE FROM shout
WHERE (chat_id, message_id) = ($1, $2)
-- :endmacro

-- :macro save_shout()
-- params: chat_id, message_id, content
INSERT INTO shout(chat_id, message_id, content)
VALUES($1, $2, $3)
ON CONFLICT DO NOTHING
-- :endmacro

-- :macro random_shout()
-- params: chat_id
SELECT content
FROM shout
TABLESAMPLE SYSTEM_ROWS(1)
WHERE chat_id = $1
-- :endmacro

-- :macro delete_by_chat()
-- params: chat_id
DELETE FROM shout
WHERE chat_id = $1
-- :endmacro

-- :macro state_for()
-- params: peer_type, id
SELECT state
FROM opt
WHERE
	peer_type = $1
	AND id = $2
-- :endmacro

-- :macro state()
-- params: peer_type, peer_id, user_id
SELECT COALESCE(
	(SELECT state FROM opt WHERE peer_type = 'PeerUser' AND id = $3),
	(SELECT state FROM opt WHERE peer_type = $1 AND id = $2),
	true) -- default state
-- :endmacro

-- :macro toggle_state()
-- params: peer_type, id, default_new_state
-- returns: new state
INSERT INTO opt (peer_type, id, state) VALUES ($1, $2, $3)
ON CONFLICT (peer_type, id) DO UPDATE
SET state = NOT opt.state
RETURNING state
-- :endmacro

-- :macro set_state()
-- params: peer_type, id, new_state
INSERT INTO opt (peer_type, id, state)
VALUES ($1, $2, $3)
ON CONFLICT (peer_type, id) DO UPDATE
SET state = EXCLUDED.state
-- :endmacro
