import aiosqlite
import os

DATABASE_PATH = "data/bot_data.db"

async def init_db():
    if not os.path.exists("data"):
        os.makedirs("data")
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        # Create table if not exists
        await db.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                pattern TEXT
            )
        """)
        # Migration: Add 'name' column to channels and api_servers if they don't exist
        try: await db.execute("ALTER TABLE channels ADD COLUMN name TEXT")
        except: pass
        try: await db.execute("ALTER TABLE api_servers ADD COLUMN name TEXT")
        except: pass
        try: await db.execute("ALTER TABLE channels ADD COLUMN pattern TEXT")
        except: pass
            
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'en'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                country TEXT,
                buy REAL,
                sell REAL,
                profit REAL,
                channel TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS api_servers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL
            )
        """)
        await db.commit()

async def get_user_language(user_id: int) -> str:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT language FROM users WHERE user_id = ?", (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else "en"

async def set_user_language(user_id: int, lang: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO users (user_id, language) VALUES (?, ?)", (user_id, lang))
        await db.commit()

async def add_channel(username: str, pattern: str, name: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO channels (username, pattern, name) VALUES (?, ?, ?)", (username, pattern, name))
        await db.commit()

async def get_channels_with_patterns():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT username, pattern, name FROM channels") as cursor:
            return await cursor.fetchall()

async def get_channel_pattern(username: str) -> str:
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT pattern FROM channels WHERE username = ? OR name = ?", (username, username)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None

async def remove_channel(username: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM channels WHERE username = ?", (username,))
        await db.commit()

async def save_opportunity(country: str, buy: float, sell: float, profit: float, channel: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("INSERT INTO opportunities (country, buy, sell, profit, channel) VALUES (?, ?, ?, ?, ?)", 
                         (country, buy, sell, profit, channel))
        await db.commit()

async def get_opportunities(limit: int = 20):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT country, buy, sell, profit, channel, timestamp FROM opportunities ORDER BY timestamp DESC LIMIT ?", (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [{"country": r[0], "buy": r[1], "sell": r[2], "profit": r[3], "channel": r[4], "timestamp": r[5]} for r in rows]

async def get_stats():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM channels") as cursor:
            channel_count = (await cursor.fetchone())[0]
        async with db.execute("SELECT COUNT(*) FROM opportunities") as cursor:
            opp_count = (await cursor.fetchone())[0]
        return {"channel_count": channel_count, "opportunity_count": opp_count}

async def add_api_server(url: str, name: str = None):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO api_servers (url, name) VALUES (?, ?)", (url, name))
        await db.commit()

async def get_api_servers():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        async with db.execute("SELECT id, url, name FROM api_servers") as cursor:
            rows = await cursor.fetchall()
            return [{"id": r[0], "url": r[1], "name": r[2]} for r in rows]

async def remove_api_server(url: str):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM api_servers WHERE url = ?", (url,))
        await db.commit()
