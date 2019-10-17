SET TIME ZONE 'UTC';

CREATE TABLE IF NOT EXISTS shout (
	chat_id BIGINT NOT NULL,
	message_id BIGINT NOT NULL PRIMARY KEY,
	content TEXT NOT NULL,
	time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP);

CREATE UNIQUE INDEX IF NOT EXISTS shout_content_unique_idx ON shout (chat_id, content);

-- https://stackoverflow.com/a/26284695/1378440
CREATE OR REPLACE FUNCTION update_time_column()
RETURNS TRIGGER AS $$ BEGIN
	IF row(NEW.content) IS DISTINCT FROM row(OLD.content) THEN
		NEW.time = CURRENT_TIMESTAMP;
		RETURN NEW;
	ELSE
		RETURN OLD; END IF; END; $$ language 'plpgsql';

CREATE TRIGGER update_shout_time
BEFORE UPDATE ON shout
FOR EACH ROW EXECUTE PROCEDURE update_time_column();

CREATE TYPE peer_type AS ENUM ('PeerChannel', 'PeerUser', 'PeerChat');

CREATE TABLE IF NOT EXISTS opt (
	id BIGINT NOT NULL,
	state BOOLEAN NOT NULL,
	peer_type peer_type NOT NULL,

	PRIMARY KEY (id, peer_type));
