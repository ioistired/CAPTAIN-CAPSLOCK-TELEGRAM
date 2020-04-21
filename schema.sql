SET TIME ZONE 'UTC';

CREATE TABLE IF NOT EXISTS shout (
	chat_id INT4 NOT NULL,
	message_id INT4 NOT NULL,
	content TEXT NOT NULL,
	time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

	PRIMARY KEY (chat_id, message_id));

CREATE UNIQUE INDEX IF NOT EXISTS shout_content_unique_idx ON shout (chat_id, content);

CREATE TYPE peer_type AS ENUM ('PeerChannel', 'PeerUser', 'PeerChat');

CREATE TABLE IF NOT EXISTS opt (
	id INT4 NOT NULL,
	state BOOLEAN NOT NULL,
	peer_type peer_type NOT NULL,

	PRIMARY KEY (id, peer_type));
