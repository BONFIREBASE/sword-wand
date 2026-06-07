import sqlite3
import os

DB_PATH = "save_data.db"

def init_db():
    """Initialize the database and create tables if they do not exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS player_stats (
            id INTEGER PRIMARY KEY,
            coins INTEGER NOT NULL DEFAULT 0,
            xp INTEGER NOT NULL DEFAULT 0,
            level INTEGER NOT NULL DEFAULT 1,
            max_hp INTEGER NOT NULL DEFAULT 100,
            lives INTEGER NOT NULL DEFAULT 3,
            has_double_dash INTEGER NOT NULL DEFAULT 0,
            has_regen INTEGER NOT NULL DEFAULT 0,
            has_cd_reduction INTEGER NOT NULL DEFAULT 0
        )
    ''')
    
    # Check if we need to migrate existing DB
    try:
        cursor.execute('ALTER TABLE player_stats ADD COLUMN has_double_dash INTEGER NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass # Column already exists
    
    try:
        cursor.execute('ALTER TABLE player_stats ADD COLUMN has_regen INTEGER NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass # Column already exists
    
    try:
        cursor.execute('ALTER TABLE player_stats ADD COLUMN has_cd_reduction INTEGER NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass # Column already exists
    
    # Check if a save exists, if not, create default row with ID 1
    cursor.execute('SELECT id FROM player_stats WHERE id = 1')
    if cursor.fetchone() is None:
        cursor.execute('''
            INSERT INTO player_stats (id, coins, xp, level, max_hp, lives, has_double_dash, has_regen, has_cd_reduction)
            VALUES (1, 0, 0, 1, 100, 3, 0, 0, 0)
        ''')
        
    conn.commit()
    conn.close()

def save_player_stats(coins, xp, level, max_hp, lives, has_double_dash, has_regen, has_cd_reduction):
    """Save player stats to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE player_stats
        SET coins = ?, xp = ?, level = ?, max_hp = ?, lives = ?, has_double_dash = ?, has_regen = ?, has_cd_reduction = ?
        WHERE id = 1
    ''', (coins, xp, level, max_hp, lives, has_double_dash, has_regen, has_cd_reduction))
    conn.commit()
    conn.close()

def load_player_stats():
    """Load player stats from the database. Returns a dictionary or default stats."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # to access columns by name
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM player_stats WHERE id = 1')
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return {
            "coins": row["coins"],
            "xp": row["xp"],
            "level": row["level"],
            "max_hp": row["max_hp"],
            "lives": row["lives"],
            "has_double_dash": bool(row["has_double_dash"]),
            "has_regen": bool(row["has_regen"]),
            "has_cd_reduction": bool(row["has_cd_reduction"])
        }
    else:
        return {
            "coins": 0,
            "xp": 0,
            "level": 1,
            "max_hp": 100,
            "lives": 3,
            "has_double_dash": False,
            "has_regen": False,
            "has_cd_reduction": False
        }
