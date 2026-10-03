-- Each search's RSS feed reads that search's own listings, newest first. Nothing led
-- with query_id, so finding them was a full scan of the items table; the feed used to
-- dodge that cost by reading the global page of 100 most recent items and discarding
-- whatever belonged to other searches, which quietly dropped listings from a search as
-- soon as the account held more than a page of them.
CREATE INDEX idx_items_query_first_seen ON items(query_id, first_seen_at DESC);