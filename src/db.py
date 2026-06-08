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
            has_cd_reduction INTEGER NOT NULL DEFAULT 0,
            has_extended_reach INTEGER NOT NULL DEFAULT 0,
            has_executioner INTEGER NOT NULL DEFAULT 0,
            has_spiked_armor INTEGER NOT NULL DEFAULT 0,
            equipped_skills TEXT NOT NULL DEFAULT ''
        )
    ''')

    try:
        cursor.execute('ALTER TABLE player_stats ADD COLUMN has_double_dash INTEGER NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE player_stats ADD COLUMN has_regen INTEGER NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE player_stats ADD COLUMN has_cd_reduction INTEGER NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE player_stats ADD COLUMN has_extended_reach INTEGER NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE player_stats ADD COLUMN has_executioner INTEGER NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE player_stats ADD COLUMN has_spiked_armor INTEGER NOT NULL DEFAULT 0')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE player_stats ADD COLUMN equipped_skills TEXT NOT NULL DEFAULT ""')
    except sqlite3.OperationalError:
        pass

    cursor.execute('SELECT id FROM player_stats WHERE id = 1')
    if cursor.fetchone() is None:
        cursor.execute('''
            INSERT INTO player_stats (id, coins, xp, level, max_hp, lives, has_double_dash, has_regen, has_cd_reduction, has_extended_reach, has_executioner, has_spiked_armor, equipped_skills)
            VALUES (1, 0, 0, 1, 100, 3, 0, 0, 0, 0, 0, 0, '')
        ''')

    conn.commit()
    conn.close()

def save_player_stats(coins, xp, level, max_hp, lives, has_double_dash, has_regen, has_cd_reduction, has_extended_reach, has_executioner, has_spiked_armor, equipped_skills):
    """Save player stats to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    eq_str = ",".join(equipped_skills) if equipped_skills else ""

    cursor.execute('''
        UPDATE player_stats
        SET coins = ?, xp = ?, level = ?, max_hp = ?, lives = ?, has_double_dash = ?, has_regen = ?, has_cd_reduction = ?, has_extended_reach = ?, has_executioner = ?, has_spiked_armor = ?, equipped_skills = ?
        WHERE id = 1
    ''', (coins, xp, level, max_hp, lives, has_double_dash, has_regen, has_cd_reduction, has_extended_reach, has_executioner, has_spiked_armor, eq_str))
    conn.commit()
    conn.close()

def load_player_stats():
    """Load player stats from the database. Returns a dictionary or default stats."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM player_stats WHERE id = 1')
    row = cursor.fetchone()
    conn.close()

    if row:
        eq_str = row["equipped_skills"]
        eq_list = eq_str.split(",") if eq_str else []
        return {
            "coins": row["coins"],
            "xp": row["xp"],
            "level": row["level"],
            "max_hp": row["max_hp"],
            "lives": row["lives"],
            "has_double_dash": bool(row["has_double_dash"]),
            "has_regen": bool(row["has_regen"]),
            "has_cd_reduction": bool(row["has_cd_reduction"]),
            "has_extended_reach": bool(row["has_extended_reach"]),
            "has_executioner": bool(row["has_executioner"]),
            "has_spiked_armor": bool(row["has_spiked_armor"]),
            "equipped_skills": eq_list
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
            "has_cd_reduction": False,
            "has_extended_reach": False,
            "has_executioner": False,
            "has_spiked_armor": False,
            "equipped_skills": []
        }

def reset_player_stats():
    """Reset player stats to default values."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE player_stats
        SET coins = 0, xp = 0, level = 1, max_hp = 100, lives = 3, has_double_dash = 0, has_regen = 0, has_cd_reduction = 0, has_extended_reach = 0, has_executioner = 0, has_spiked_armor = 0, equipped_skills = ''
        WHERE id = 1
    ''')
    conn.commit()
    conn.close()
