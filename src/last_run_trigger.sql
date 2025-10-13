ALTER TABLE last_run ADD CONSTRAINT one_row CHECK (id = 1);
CREATE OR REPLACE FUNCTION limit_one_row()
RETURNS trigger AS $$
BEGIN
  IF (SELECT COUNT(*) FROM last_run) >= 1 THEN
    RAISE EXCEPTION 'Can only be one row in last_run table';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
CREATE TRIGGER last_run_limit_insert
BEFORE INSERT ON last_run
FOR EACH ROW EXECUTE FUNCTION limit_one_row();