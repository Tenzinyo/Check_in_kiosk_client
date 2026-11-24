-- Enable foreign key enforcement in SQLite
PRAGMA foreign_keys = ON;

-- Create Table
CREATE TABLE IF NOT EXISTS customers(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone_number TEXT UNIQUE NOT NULL,
    visits_count INTEGER NOT NULL DEFAULT 0,
    available_discounts INTEGER NOT NULL DEFAULT 0,
    referred_by INTEGER REFERENCES customers(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Visits log table
CREATE TABLE IF NOT EXISTS visits(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Rewards table
CREATE TABLE IF NOT EXISTS rewards(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    reason TEXT NOT 
    NULL CHECK(reason IN('REFERRAL','VISIT')),
    status TEXT NOT NULL DEFAULT 'AVAILABLE' CHECK(status IN ('AVAILABLE', 'REDEEMED')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    redeemed_at DATETIME
);


-- track phone number
CREATE INDEX IF NOT EXISTS idx_phone_number ON customers(phone_number);








