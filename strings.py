STRINGS = {
    "welcome": {
        "en": "👋 Welcome to Arbitrage Bot!\n\nThis bot helps you monitor Telegram channels for profitable number sales.\nUse the menu below to get started.",
        "ar": "👋 أهلاً بك في بوت التحكيم!\n\nهذا البوت يساعدك في مراقبة قنوات التليجرام للبحث عن فرص ربح في بيع الأرقام.\nاستخدم القائمة بالأسفل للبدء."
    },
    "btn_add_account": {
        "en": "📱 Add Account",
        "ar": "📱 إضافة حساب"
    },
    "btn_add_channel": {
        "en": "➕ Add Channel",
        "ar": "➕ إضافة قناة"
    },
    "btn_list_channels": {
        "en": "📊 Tracked Channels",
        "ar": "📊 القنوات المتابعة"
    },
    "btn_delete_channel": {
        "en": "❌ Delete Channel",
        "ar": "❌ حذف قناة"
    },
    "btn_manual_check": {
        "en": "🔄 Manual Check",
        "ar": "🔄 فحص يدوي"
    },
    "btn_back": {
        "en": "Back 🔙",
        "ar": "رجوع 🔙"
    },
    "add_account_prompt": {
        "en": "Please send the phone number with the country code (e.g. +20123456789):",
        "ar": "قم بإرسال رقم الهاتف مسبوقاً بكود الدولة (مثال: +20123456789):"
    },
    "code_sent": {
        "en": "Verification code sent. Please send the code here:",
        "ar": "تم إرسال كود التحقق. قم بإرسال الكود هنا:"
    },
    "login_success": {
        "en": "✅ Successfully logged in!",
        "ar": "✅ تم تسجيل الدخول بنجاح!"
    },
    "password_needed": {
        "en": "🔐 Two-Step Verification enabled. Send your password:",
        "ar": "🔐 أرسل كلمة السر (2FA):"
    },
    "error": {
        "en": "❌ Error: {}",
        "ar": "❌ خطأ: {}"
    },
    "add_channel_prompt": {
        "en": "Please send the channel username (e.g. @channel_name):",
        "ar": "يرجى إرسال معرف القناة (مثال: @channel_name):"
    },
    "channel_added": {
        "en": "✅ Channel {} added successfully!\n\n💡 Thanks to the new AI system, the bot will automatically extract country prices from this channel regardless of language or format.",
        "ar": "✅ تم إضافة القناة {} بنجاح!\n\n💡 بفضل نظام الذكاء الاصطناعي الجديد، سيقوم البوت باستخراج أسعار الدول من هذه القناة تلقائياً مهما كانت لغتها أو شكلها."
    },
    "no_channels": {
        "en": "No tracked channels found.",
        "ar": "لا توجد قنوات متابعة."
    },
    "current_channels": {
        "en": "📋 Current Channels:\n",
        "ar": "📋 القنوات الحالية:\n"
    },
    "delete_channel_prompt": {
        "en": "Select a channel to delete:",
        "ar": "اختر القناة لحذفها:"
    },
    "channel_deleted": {
        "en": "✅ Channel {} deleted.",
        "ar": "✅ تم حذف القناة {}."
    },
    "starting_manual_check": {
        "en": "🔄 Starting manual check...",
        "ar": "🔄 جاري بدء الفحص اليدوي..."
    },
    "no_account_linked": {
        "en": "❌ No account linked! Please add an account first.",
        "ar": "❌ لم يتم ربط حساب! يرجى إضافة حساب أولاً."
    },
    "manual_check_success": {
        "en": "✅ **Manual Check Complete**\n\n📊 **Current Results:**\n",
        "ar": "✅ **تم الفحص بنجاح**\n\n📊 **النتائج الحالية:**\n"
    },
    "manual_check_empty": {
        "en": "ℹ️ **Manual Check Complete, but no profit opportunities found (greater than $0.05).**\n\n📊 **Current Results:**\n",
        "ar": "ℹ️ **تم الفحص بنجاح، ولكن لا توجد فرص ربح (أكبر من 0.05$).**\n\n📊 **النتائج الحالية:**\n"
    },
    "buy_sell_profit": {
        "en": "🌍 {}:\nBuy ${}\nSell ${}\nProfit: ${}\n+-----------+-------------+----------+----------|\n",
        "ar": "🌍 {}:\nشراء ${}\nبيع ${}\nالربح: ${}\n+-----------+-------------+----------+----------|\n"
    },
    "profit_alert": {
        "en": "• New Profit Opportunity 🔔\n\n• For country :- {}\n• Buy :- ${} 💵\n\n• Sell :- ${} 💵\n• Profit :- ${} 💵\n\n• Sell Source :- {}\n• Buy Source :- {}",
        "ar": "• New Profit Opportunity 🔔\n\n• For country :- {}\n• Buy :- ${} 💵\n\n• Sell :- ${} 💵\n• Profit :- ${} 💵\n\n• Sell Source :- {}\n• Buy Source :- {}"
    },
    "lang_prompt": {
        "en": "Please choose your preferred language:",
        "ar": "الرجاء اختيار لغتك المفضلة:"
    },
    "lang_changed": {
        "en": "Language changed to English 🇬🇧",
        "ar": "تم تغيير اللغة إلى العربية 🇸🇦"
    }
}

def _(key: str, lang: str = "en", *args) -> str:
    """
    Returns the translated string for a given key.
    If the key doesn't exist, it returns the key itself.
    If args are provided, they will be formatted into the string.
    """
    text = STRINGS.get(key, {}).get(lang, STRINGS.get(key, {}).get("en", key))
    if args:
        return text.format(*args)
    return text
