-- :macro update_shout()
-- params: message_id, content
UPDATE shout
SET content = $2
WHERE message_id = $1
-- :endmacro

-- :macro delete_shout()
-- params: message_id
DELETE FROM shout
WHERE message_id = $1
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
WHERE chat_id = $1
ORDER BY RANDOM()
LIMIT 1
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
-- params: chat_id, user_id
SELECT COALESCE(
	(SELECT state FROM opt WHERE peer_type = 'PeerUser' AND id = $2),
	(SELECT state FROM opt WHERE peer_type = 'PeerChat' AND id = $1),
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
