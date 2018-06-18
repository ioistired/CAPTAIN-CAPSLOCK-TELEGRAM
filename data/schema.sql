CREATE TABLE IF NOT EXISTS shout (
	hash VARCHAR(100) NOT NULL PRIMARY KEY UNIQUE,
	id BIGINT NOT NULL UNIQUE
	time TIMESTAMP WITH TIMEZONE DEFAULT (now() AT TIME ZONE 'UTC')
);

-- https://stackoverflow.com/a/26284695/1378440
CREATE OR REPLACE FUNCTION update_time_column()
RETURNS TRIGGER AS $$
BEGIN
	IF row(NEW.hash) IS DISTINCT FROM row(OLD.hash) THEN
		NEW.time = now() at time zone 'UTC';
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
