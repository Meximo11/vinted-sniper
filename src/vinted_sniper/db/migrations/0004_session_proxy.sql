-- The route a session's cookie was minted through, and the one it must be replayed
-- from. A cookie fetched over a proxy and then replayed directly is exactly the
-- inconsistency anti-bot systems look for, and until this column existed the route was
-- held only in memory: every restart quietly promoted a proxied session to a direct one.
--
-- Nullable: a session created without a proxy stores NULL and is replayed direct, which
-- is what it was created as. Existing rows get NULL rather than a guess.
ALTER TABLE sessions ADD COLUMN proxy TEXT;
