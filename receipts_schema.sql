-- receipts table
CREATE TABLE IF NOT EXISTS receipt (
	receipt_id integer PRIMARY KEY,
	person_id integer NOT NULL,
	shop_name text,
	total real NOT NULL,
	shopping_date date,
	FOREIGN KEY (person_id) REFERENCES person (person_id)
--	PRIMARY KEY (receipt_id, person_id, shopping_date) not primary key but should be unq
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
    phone text UNIQUE NOT NULL,
    name text NOT NULL
);