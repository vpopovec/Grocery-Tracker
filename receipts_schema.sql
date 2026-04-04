-- receipts table
CREATE TABLE IF NOT EXISTS receipt (
	receipt_id integer PRIMARY KEY,
	person_id integer NOT NULL,
	shop_name text,
	total real NOT NULL,
	shopping_date datetime,
	FOREIGN KEY (person_id) REFERENCES person (person_id)
	UNIQUE(person_id, shop_name, shopping_date, total) ON CONFLICT REPLACE  -- ensure unique receipts for 1 person
);

-- items table
CREATE TABLE IF NOT EXISTS item (
	item_id integer PRIMARY KEY,
    price real NOT NULL,
    amount real,
    name text NOT NULL,  -- don't forget to make the name SQL-safe
	receipt_id integer,
	FOREIGN KEY (receipt_id) REFERENCES receipts (receipt_id)
);

-- persons table
CREATE TABLE IF NOT EXISTS person (
    person_id integer PRIMARY KEY,
    email text UNIQUE NOT NULL,
    username text UNIQUE NOT NULL,
    name text NOT NULL,
    password_hash text
);

-- password reset tokens (dev-only flow; token stored as SHA-256 hex)
CREATE TABLE IF NOT EXISTS password_reset_token (
    id integer PRIMARY KEY,
    person_id integer NOT NULL,
    token_hash text NOT NULL,
    expires_at datetime NOT NULL,
    used_at datetime,
    FOREIGN KEY (person_id) REFERENCES person (person_id)
);

CREATE INDEX IF NOT EXISTS ix_password_reset_token_token_hash
    ON password_reset_token (token_hash);

-- scans table
CREATE TABLE IF NOT EXISTS scan (
    scan_id integer PRIMARY KEY,
    f_name text NOT NULL UNIQUE,
    person_id integer NOT NULL,
    receipt_id integer NOT NULL,
    FOREIGN KEY (person_id) REFERENCES person (person_id)
    FOREIGN KEY (receipt_id) REFERENCES receipt (receipt_id)
);

-- this deletes items only on explicit DELETE, not on REPLACE...
CREATE TRIGGER IF NOT EXISTS remove_items AFTER DELETE ON receipt
BEGIN
  DELETE FROM item
  WHERE receipt_id = OLD.receipt_id;
END;