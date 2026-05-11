import os

# Telegram API Credentials
API_ID = int(os.getenv("API_ID", "28660455"))
API_HASH = os.getenv("API_HASH", "02bd2ca66c433c5b5b396f6ab34c9c70")
BOT_TOKEN = os.getenv("BOT_TOKEN", "8757913865:AAHx_yT-esbVtP9PrgCbI_5zEt7BDWSF4ws")

# Monitoring Settings
ADMIN_ID = int(os.getenv("ADMIN_ID", "8741285999"))

# Profit Margin
MIN_PROFIT = float(os.getenv("MIN_PROFIT", "0.05"))

# Web Dashboard Settings
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://your-ngrok-url.ngrok-free.app")
# Railway and other hosts provide 'PORT' env var
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "8080")))
