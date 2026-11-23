import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "kiosk.db"
schema_path = Path(__file__).parent / "schema.sql"

def init_db():
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
    print(f"Database initialized successfully at: {db_path}")

if __name__ == "__main__":
    init_db()
# const Database = require('better-sqlite3');
# const fs = require('fs');
# const path = require('path');

# const dbPath = path.join(__dirname, 'kiosk.db');
# const db = new Database(dbPath);

# const schema = fs.readFileSync(path.join(__dirname, 'schema.sql'), 'utf-8');
# db.exec(schema);

# console.log('Database initialized successfully.');
# module.exports = db;