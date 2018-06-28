CREATE TABLE IF NOT EXISTS shout (
	guild_or_user BIGINT NOT NULL,
	message BIGINT NOT NULL PRIMARY KEY,
	content TEXT NOT NULL,
	time TIMESTAMP WITH TIME ZONE DEFAULT (now() AT TIME ZONE 'UTC')
);
-- old constraint on message content being globally unique
ALTER TABLE shout DROP CONSTRAINT IF EXISTS shout_content_key;
CREATE INDEX IF NOT EXISTS shout_guild_or_user_idx ON shout (guild_or_user);
CREATE UNIQUE INDEX IF NOT EXISTS shout_guild_content_unique_idx ON shout (guild_or_user, content);

-- https://stackoverflow.com/a/26284695/1378440
CREATE OR REPLACE FUNCTION update_time_column()
RETURNS TRIGGER AS $$
BEGIN
	IF row(NEW.content) IS DISTINCT FROM row(OLD.content) THEN
		NEW.time = now() AT TIME ZONE 'UTC';
		RETURN NEW;
	ELSE
		RETURN OLD;
	END IF;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_shout_time ON shout;

CREATE TRIGGER update_shout_time
BEFORE UPDATE ON shout
FOR EACH ROW EXECUTE PROCEDURE update_time_column();
