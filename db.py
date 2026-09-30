import json
import sqlite3
from config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS positions (symbol TEXT PRIMARY KEY, qty REAL, entry REAL,
    sl REAL, tp REAL, entry_ms INTEGER);
CREATE TABLE IF NOT EXISTS trades (id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT,
    entry_ms INTEGER, exit_ms INTEGER, entry REAL, exit REAL, qty REAL,
    sl REAL, tp REAL, pnl REAL, exit_reason TEXT);
CREATE TABLE IF NOT EXISTS signals (ts INTEGER, symbol TEXT, price REAL, score INTEGER,
    news REAL, action TEXT, reasons TEXT);
CREATE TABLE IF NOT EXISTS equity (ts INTEGER, value REAL);
CREATE TABLE IF NOT EXISTS runs (ts INTEGER, ok INTEGER, error TEXT);
"""

def connect(path=DB_PATH):
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    return con

def get(con, key, default=None):
    row = con.execute("SELECT value FROM state WHERE key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else default

def put(con, key, value):
    con.execute("INSERT OR REPLACE INTO state VALUES (?,?)", (key, json.dumps(value)))
