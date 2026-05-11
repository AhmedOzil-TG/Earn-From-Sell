import os

# Telegram API Credentials
API_ID = 28660455
API_HASH = "02bd2ca66c433c5b5b396f6ab34c9c70"
BOT_TOKEN = "8757913865:AAHx_yT-esbVtP9PrgCbI_5zEt7BDWSF4ws"

# Monitoring Settings
ADMIN_ID = 8741285999
# Note: I should probably ask for the user's ID or get it from the bot interaction.
# For now, I'll leave it as a variable.

# Channels to monitor (Username or ID)
CHANNELS_TO_MONITOR = [
    "@example_channel" # User will need to update this
]

# Profit Margin
MIN_PROFIT = 0.05

# Web Dashboard Settings
# Note: Telegram Mini Apps require HTTPS. Use a service like ngrok to get an HTTPS URL for local testing.
WEBAPP_URL = "https://your-ngrok-url.ngrok-free.app" 
WEB_PORT = 8000
