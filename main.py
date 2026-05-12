import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError

from config import API_ID, API_HASH, BOT_TOKEN, ADMIN_ID, MIN_PROFIT, WEBAPP_URL, WEB_PORT
from scrapers import parse_price_message, fetch_buy_prices_api
from database import (init_db, add_channel, get_channels_with_patterns, remove_channel, 
                     get_channel_pattern, get_user_language, set_user_language, save_opportunity, 
                     get_opportunities, get_stats, add_api_server, get_api_servers, remove_api_server)
from strings import _, STRINGS

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn
from pydantic import BaseModel
import json
import pycountry
import html

def get_country_display(iso_code):
    if not iso_code or len(iso_code) != 2:
        return iso_code
    try:
        emoji = chr(ord(iso_code[0].upper()) + 127397) + chr(ord(iso_code[1].upper()) + 127397)
        country = pycountry.countries.get(alpha_2=iso_code.upper())
        name = country.name if country else iso_code
        return f"{name}{emoji}"
    except:
        return iso_code

app = FastAPI()
# Store recent opportunities in memory for faster access, or use DB
RECENT_OPPS = []

# Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Bots
from aiogram.client.default import DefaultBotProperties
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()
client = TelegramClient('data/arbitrage_session', API_ID, API_HASH)

# States
class BotStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_password = State()
    waiting_for_channel_username = State()
    waiting_for_channel_sample = State()
    waiting_for_channel_confirm = State()
    waiting_for_channel_pattern = State()
    waiting_for_channel_delete = State()
    waiting_for_manual_check_choice = State()

# Keyboards
def main_keyboard(lang="en"):
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=_("btn_add_account", lang)), KeyboardButton(text=_("btn_add_channel", lang))],
        [KeyboardButton(text=_("btn_manual_check", lang)), KeyboardButton(text=_("btn_list_channels", lang))],
        [KeyboardButton(text=_("btn_delete_channel", lang))]
    ], resize_keyboard=True)

# --- Aiogram Handlers ---

@dp.message(Command("start"))
@dp.message(F.text.in_([STRINGS["btn_back"]["en"], STRINGS["btn_back"]["ar"]]))
async def start_cmd(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
    
    # New welcome message and inline button
    welcome_text = "Welcome to the Panel! 🚀\nClick the button below to open."
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Open", web_app=WebAppInfo(url=WEBAPP_URL))]
    ])
    
    lang = await get_user_language(message.from_user.id)
    await state.clear()
    await message.answer(welcome_text, reply_markup=kb)

# -- Login Flow --
@dp.message(F.text.in_([STRINGS["btn_add_account"]["en"], STRINGS["btn_add_account"]["ar"]]))
async def add_account_start(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    await message.answer(_("add_account_prompt", lang))
    await state.set_state(BotStates.waiting_for_phone)

@dp.message(BotStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    phone = message.text.strip()
    await state.update_data(phone=phone)
    try:
        if not client.is_connected(): await client.connect()
        result = await client.send_code_request(phone)
        await state.update_data(phone_code_hash=result.phone_code_hash)
        await message.answer(_("code_sent", lang))
        await state.set_state(BotStates.waiting_for_code)
    except Exception as e:
        await message.answer(_("error", lang, e))
        await state.clear()

@dp.message(BotStates.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    data = await state.get_data()
    code = message.text.strip()
    try:
        await client.sign_in(phone=data['phone'], code=code, phone_code_hash=data['phone_code_hash'])
        await message.answer(_("login_success", lang))
        await state.clear()
    except SessionPasswordNeededError:
        await message.answer(_("password_needed", lang))
        await state.set_state(BotStates.waiting_for_password)
    except Exception as e:
        await message.answer(_("error", lang, e))
        await state.clear()

@dp.message(BotStates.waiting_for_password)
async def process_password(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    try:
        await client.sign_in(password=message.text.strip())
        await message.answer(_("login_success", lang))
        await state.clear()
    except Exception as e:
        await message.answer(_("error", lang, e))
        await state.clear()

# -- Channel Management --
@dp.message(F.text.in_([STRINGS["btn_add_channel"]["en"], STRINGS["btn_add_channel"]["ar"]]))
async def add_channel_start(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    await message.answer(_("add_channel_prompt", lang))
    await state.set_state(BotStates.waiting_for_channel_username)

@dp.message(BotStates.waiting_for_channel_username)
async def process_channel_username(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    username = message.text.strip()
    # Only add @ if it doesn't look like an ID, a link, or already has an @
    if not any(username.startswith(p) for p in ["@", "-", "http"]) and not username.isdigit():
        username = "@" + username
    
    # We no longer need patterns! The bot will universally extract phone prefixes and prices.
    await add_channel(username, "UNIVERSAL")
    await message.answer(_("channel_added", lang, username), reply_markup=main_keyboard(lang))
    await state.clear()

@dp.message(F.text.in_([STRINGS["btn_list_channels"]["en"], STRINGS["btn_list_channels"]["ar"]]))
async def list_channels(message: types.Message):
    lang = await get_user_language(message.from_user.id)
    channels = await get_channels_with_patterns()
    if not channels:
        await message.answer(_("no_channels", lang))
    else:
        text = _("current_channels", lang)
        for user, pat in channels:
            text += f"🔹 {user}\n"
        await message.answer(text)

@dp.message(F.text.in_([STRINGS["btn_delete_channel"]["en"], STRINGS["btn_delete_channel"]["ar"]]))
async def delete_channel_start(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    channels = await get_channels_with_patterns()
    if not channels:
        await message.answer(_("no_channels", lang))
        return
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=ch[0])] for ch in channels] + [[KeyboardButton(text=_("btn_back", lang))]], resize_keyboard=True)
    await message.answer(_("delete_channel_prompt", lang), reply_markup=kb)
    await state.set_state(BotStates.waiting_for_channel_delete)

@dp.message(BotStates.waiting_for_channel_delete)
async def process_delete_channel(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    if message.text in [STRINGS["btn_back"]["en"], STRINGS["btn_back"]["ar"]]:
        return await start_cmd(message, state)
    username = message.text.strip()
    await remove_channel(username)
    await message.answer(_("channel_deleted", lang, username), reply_markup=main_keyboard(lang))
    await state.clear()

# -- Manual Check --
@dp.message(F.text.in_([STRINGS["btn_manual_check"]["en"], STRINGS["btn_manual_check"]["ar"]]))
async def manual_check_start(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    channels = await get_channels_with_patterns()
    if not channels:
        await message.answer(_("no_channels", lang))
        return
    kb = ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=ch[0])] for ch in channels] + [[KeyboardButton(text="All Channels")], [KeyboardButton(text=_("btn_back", lang))]], resize_keyboard=True)
    await message.answer(_("delete_channel_prompt", lang).replace("حذفها", "فحصها").replace("delete", "check"), reply_markup=kb)
    await state.set_state(BotStates.waiting_for_manual_check_choice)

@dp.message(BotStates.waiting_for_manual_check_choice)
async def process_manual_check(message: types.Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    choice = message.text.strip()
    if choice in [STRINGS["btn_back"]["en"], STRINGS["btn_back"]["ar"]]:
        return await start_cmd(message, state)
    
    await message.answer(_("starting_manual_check", lang))
    
    servers_data = await get_api_servers()
    server_urls = [s['url'] for s in servers_data]
    buy_prices = await fetch_buy_prices_api(server_urls)
    
    to_check = []
    if choice == "All Channels" or choice == "كل القنوات":
        to_check = await get_channels_with_patterns()
    else:
        pattern = await get_channel_pattern(choice)
        if pattern: to_check = [(choice, pattern)]
    
    if not to_check:
        await message.answer(_("error", lang, "Channel not found."))
        return

    all_checks = []
    opportunities = []
    if not client.is_connected(): await client.connect()

    for channel_user, pattern in to_check:
        try:
            # If it's a numeric ID, convert to int for Telethon
            target = channel_user
            if str(target).startswith("-") or str(target).isdigit():
                try: target = int(target)
                except: pass
                
            msgs = await client.get_messages(target, limit=30)
            
            latest_prices = {} # Dictionary to store only the latest price for each country
            for msg in msgs:
                if not msg.text: continue
                results = parse_price_message(msg.text, pattern)
                for country, sell in results:
                    if country and country not in latest_prices:
                        latest_prices[country] = sell
            
            for country, sell in latest_prices.items():
                if country in buy_prices:
                    buy_info = buy_prices[country][0]
                    buy = buy_info["price"]
                    profit = sell - buy
                    all_checks.append((country, buy, sell, profit, channel_user))
                    if profit >= MIN_PROFIT:
                        opportunities.append((country, buy, sell, profit, channel_user))
                else:
                    all_checks.append((country, "N/A", sell, 0.0, channel_user))
        except Exception as e: logger.error(f"Error checking {channel_user}: {e}")

    if not all_checks:
        await message.answer(_("error", lang, "No valid messages found."))
    elif not opportunities:
        summary = _("manual_check_empty", lang)
        for c, b, s, p, ch in all_checks:
            summary += _("buy_sell_profit", lang, c, b, s, f"{p:.2f}")
        await message.answer(summary, reply_markup=main_keyboard(lang))
    else:
        report = _("manual_check_success", lang)
        for c, b, s, p, ch in opportunities:
            report += _("buy_sell_profit", lang, c, b, s, f"{p:.2f}")
        await message.answer(report, reply_markup=main_keyboard(lang))
    await state.clear()

# --- Telethon Monitoring ---
@client.on(events.NewMessage(incoming=True))
async def telethon_handler(event):
    try:
        if not event.message.message: return
        chat_id = str(event.chat_id)
        chat_username = getattr(event.chat, 'username', None) if hasattr(event, 'chat') else None
        
        if not chat_username:
            try:
                chat = await event.get_chat()
                chat_username = getattr(chat, 'username', None)
            except Exception:
                pass
        
        channels = await get_channels_with_patterns()
        matched_channel_name = None
        pattern = None
        
        for db_user, db_pattern in channels:
            db_u_clean = db_user.replace("https://t.me/", "").replace("@", "").strip()
            
            if chat_username and chat_username.lower() == db_u_clean.lower():
                pattern = db_pattern
                matched_channel_name = db_user
                break
            elif chat_id == db_user or chat_id.replace("-100", "") == db_user.replace("-100", ""):
                pattern = db_pattern
                matched_channel_name = db_user
                break

        if not pattern: return

        results = parse_price_message(event.message.message, pattern)
        if not results: return
        
        servers_data = await get_api_servers()
        server_urls = [s['url'] for s in servers_data]
        buy_prices = await fetch_buy_prices_api(server_urls)
        
        for country, sell in results:
            if country in buy_prices:
                profitable_sources = []
                for buy_info in buy_prices[country]:
                    buy = buy_info["price"]
                    server_url = buy_info["server"]
                    profit = sell - buy
                    if profit >= MIN_PROFIT:
                        profitable_sources.append({"buy": buy, "profit": profit, "server": server_url})
                
                if profitable_sources:
                    best = profitable_sources[0]
                    # Save the best to database for dashboard
                    await save_opportunity(country, best["buy"], sell, best["profit"], matched_channel_name)
                    
                    country_display = get_country_display(country)
                    safe_channel = html.escape(matched_channel_name)
                    msg = f"• New Profit Opportunity 🔔\n\n• For country :- {country_display}\n• Sell :- ${sell} 💵\n• Sell Source :- {safe_channel}\n\n🛒 <b>Buy Options:</b>\n"
                    
                    for src in profitable_sources:
                        safe_server = html.escape(src['server'])
                        msg += f"• Buy :- ${src['buy']} 💵\n• Profit :- ${src['profit']:.2f} 💵\n• Buy Source :- {safe_server}\n\n"
                    
                    await bot.send_message(ADMIN_ID, msg, disable_web_page_preview=True, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Telethon handler error: {e}")

# -- Language Selection --
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

@dp.message(Command("lang"))
async def lang_cmd(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="English 🇬🇧", callback_data="lang_en")],
        [InlineKeyboardButton(text="العربية 🇸🇦", callback_data="lang_ar")]
    ])
    lang = await get_user_language(message.from_user.id)
    await message.answer(_("lang_prompt", lang), reply_markup=kb)

@dp.callback_query(F.data.startswith("lang_"))
async def process_lang_selection(callback: CallbackQuery):
    selected_lang = callback.data.split("_")[1]
    await set_user_language(callback.from_user.id, selected_lang)
    await callback.message.edit_text(_("lang_changed", selected_lang))
    await callback.message.answer(_("welcome", selected_lang), reply_markup=main_keyboard(selected_lang))

# --- FastAPI Routes ---
@app.get("/", response_class=HTMLResponse)
async def get_dashboard():
    import os
    template_path = os.path.join(os.path.dirname(__file__), "templates", "dashboard.html")
    with open(template_path, "r", encoding="utf-8") as f:
        return f.read()

@app.get("/api/dashboard/data")
async def get_dashboard_data():
    stats = await get_stats()
    opps = await get_opportunities(10)
    channels_raw = await get_channels_with_patterns()
    channels = [{"username": c[0], "pattern": c[1]} for c in channels_raw]
    api_servers = await get_api_servers()
    
    return {
        "channels": channels,
        "opportunities": opps,
        "api_servers": api_servers,
        "min_profit": MIN_PROFIT
    }

class ChannelData(BaseModel):
    username: str

@app.post("/api/dashboard/channels")
async def api_add_channel(data: ChannelData):
    await add_channel(data.username, "UNIVERSAL")
    return {"status": "ok"}

@app.delete("/api/dashboard/channels/{username}")
async def api_delete_channel(username: str):
    await remove_channel(username)
    return {"status": "ok"}

class ApiServerData(BaseModel):
    url: str

@app.post("/api/dashboard/api-servers")
async def api_add_server(data: ApiServerData):
    await add_api_server(data.url)
    return {"status": "ok"}

@app.delete("/api/dashboard/api-servers")
async def api_delete_server(data: ApiServerData):
    await remove_api_server(data.url)
    return {"status": "ok"}

@app.post("/api/dashboard/settings")
async def api_save_settings(data: dict):
    global MIN_PROFIT
    if "min_profit" in data:
        MIN_PROFIT = float(data["min_profit"])
    return {"status": "ok"}

# --- Auth & Account API ---
class LoginPhone(BaseModel):
    phone: str

@app.post("/api/auth/send-code")
async def api_send_code(data: LoginPhone):
    try:
        if not client.is_connected(): await client.connect()
        result = await client.send_code_request(data.phone)
        return {"status": "ok", "phone_code_hash": result.phone_code_hash}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class LoginCode(BaseModel):
    phone: str
    code: str
    phone_code_hash: str

@app.post("/api/auth/verify-code")
async def api_verify_code(data: LoginCode):
    try:
        await client.sign_in(phone=data.phone, code=data.code, phone_code_hash=data.phone_code_hash)
        return {"status": "ok"}
    except SessionPasswordNeededError:
        return {"status": "password_needed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class LoginPassword(BaseModel):
    password: str

@app.post("/api/auth/verify-password")
async def api_verify_password(data: LoginPassword):
    try:
        await client.sign_in(password=data.password)
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/auth/logout")
async def api_logout():
    try:
        if client.is_connected():
            await client.log_out()
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/auth/status")
async def api_auth_status():
    connected = await client.is_user_authorized() if client.is_connected() else False
    me = await client.get_me() if connected else None
    return {
        "connected": connected,
        "user": me.username if me else None,
        "phone": me.phone if me else None
    }

# --- Manual Check API ---
class ManualCheckRequest(BaseModel):
    server: str
    channel: str

@app.post("/api/dashboard/manual-check")
async def api_manual_check(req: ManualCheckRequest):
    try:
        # Fetch buy prices ONLY from the selected server
        buy_prices = await fetch_buy_prices_api([req.server])
        
        # Get pattern for the selected channel
        pattern = await get_channel_pattern(req.channel)
        if not pattern: pattern = "UNIVERSAL"
        
        if not client.is_connected(): await client.connect()
        
        results_summary = []
        
        # If it's a numeric ID, convert to int for Telethon
        target = req.channel
        if str(target).startswith("-") or str(target).isdigit():
            try: target = int(target)
            except: pass

        msgs = await client.get_messages(target, limit=20)
        
        latest_prices = {}
        for msg in msgs:
            if not msg.text: continue
            found = parse_price_message(msg.text, pattern)
            for country, sell in found:
                if country not in latest_prices: latest_prices[country] = sell
        
        for country, sell in latest_prices.items():
            if country in buy_prices:
                for buy_info in buy_prices[country]:
                    buy = buy_info["price"]
                    profit = sell - buy
                    if profit > 0:
                        results_summary.append({
                            "country": country,
                            "buy": buy,
                            "sell": sell,
                            "profit": round(profit, 2),
                            "server": buy_info["server"],
                            "channel": req.channel
                        })
        return {"status": "ok", "results": results_summary}
    except Exception as e:
        logger.error(f"Manual check error: {e}")
        return {"status": "error", "message": str(e)}

# --- Main ---
async def main():
    logger.info("--- Starting Arbitrage Bot System ---")
    await init_db()
    logger.info("Database initialized.")
    
    # Set bot commands menu
    await bot.set_my_commands([
        types.BotCommand(command="start", description="Start the bot / القائمة الرئيسية"),
        types.BotCommand(command="lang", description="Change Language / تغيير اللغة")
    ])

    from aiogram.types import MenuButtonWebApp, WebAppInfo
    # Set the 'Open' button next to Menu
    await bot.set_chat_menu_button(
        menu_button=MenuButtonWebApp(text="Open", web_app=WebAppInfo(url=WEBAPP_URL))
    )

    try:
        logger.info("Connecting Telethon client...")
        await client.connect()
        logger.info("Telethon client connected.")
        
        # Fetch dialogs to populate entity cache, so incoming channel messages aren't ignored
        if await client.is_user_authorized():
            logger.info("User is authorized. Fetching dialogs to cache entities...")
            await client.get_dialogs(limit=100)
            logger.info("Dialogs cached.")
            
    except Exception as e:
        logger.error(f"Failed to connect Telethon: {e}")

    # Run FastAPI in background
    logger.info(f"Starting Web Dashboard on port {WEB_PORT}...")
    config = uvicorn.Config(app, host="0.0.0.0", port=WEB_PORT, log_level="info")
    server = uvicorn.Server(config)
    
    # We use create_task to run uvicorn alongside aiogram
    asyncio.create_task(server.serve())
    
    logger.info("Starting Bot Polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("System stopped.")
