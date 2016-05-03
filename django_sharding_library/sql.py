postgres_shard_id_function_sql = """CREATE OR REPLACE FUNCTION next_sharded_id(OUT result bigint) AS $$
DECLARE
    start_epoch bigint := %(shard_epoch)d;
    seq_id bigint;
    now_millis bigint;
    shard_id int := %(shard_id)d;
BEGIN
    -- there is a typo here in the online example, which is corrected here
    SELECT nextval('%(sequence_name)s') %% 1024 INTO seq_id;

    SELECT FLOOR(EXTRACT(EPOCH FROM clock_timestamp()) * 1000) INTO now_millis;
    result := (now_millis - start_epoch) << 23;
    result := result | (shard_id << 10);
    result := result | (seq_id);
END;
$$ LANGUAGE PLPGSQL;"""
