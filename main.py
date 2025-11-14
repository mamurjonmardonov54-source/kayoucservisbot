import telebot
from telebot import types
import json
import random
from keep_alive import keep_alive

# === CONFIG ===
def load_config():
    with open("config.json", "r") as f:
        return json.load(f)

def save_config(data):
    with open("config.json", "w") as f:
        json.dump(data, f, indent=4)

config = load_config()
bot = telebot.TeleBot(config["bot_token"])
ADMIN = int(config["admin_id"])


# =====================================================
# START
# =====================================================
@bot.message_handler(commands=["start"])
def start(message):
    user_id = str(message.from_user.id)

    if user_id not in config["users"]:
        config["users"][user_id] = {"balance": 0, "action": None}
        save_config(config)

    # Majburiy kanal bo'lsa tekshiradi
    if config["mandatory_channel"]:
        try:
            member = bot.get_chat_member(config["mandatory_channel"], message.from_user.id)
            if member.status not in ("member", "administrator", "creator"):
                join = types.InlineKeyboardMarkup()
                join.add(types.InlineKeyboardButton("Kanalga qo‘shilish", url=f"https://t.me/{config['mandatory_channel'].replace('@','')}"))
                bot.send_message(message.chat.id, "⛔ Botdan foydalanish uchun kanalga obuna bo‘ling!", reply_markup=join)
                return
        except:
            pass

    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add("💳 Balansni to‘ldirish")
    menu.add("🛒 UC sotib olish", "🎫 RP sotib olish")
    menu.add("📦 Paketlar")
    menu.add("📞 Admin bilan aloqa")

    bot.send_message(message.chat.id, "Xush kelibsiz!", reply_markup=menu)


# =====================================================
# BALANCE TOP UP
# =====================================================
@bot.message_handler(func=lambda m: m.text == "💳 Balansni to‘ldirish")
def fill_balance(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🇺🇿 O‘zbekiston", callback_data="reg_uz"),
        types.InlineKeyboardButton("🇷🇺 Rossiya", callback_data="reg_ru"),
        types.InlineKeyboardButton("🇰🇿 Qozog‘iston", callback_data="reg_kz")
    )
    bot.send_message(message.chat.id, "Davlatni tanlang:", reply_markup=markup)


@bot.callback_query_handler(func=lambda c: c.data.startswith("reg_"))
def region_select(call):
    region = call.data.split("_")[1]
    uid = str(call.from_user.id)

    config["users"][uid]["action"] = f"amount_{region}"
    save_config(config)

    bot.send_message(call.message.chat.id, "Miqdorni kiriting (10000–10000000):")


# =====================================================
# MIQDORNI QABUL QILISH
# =====================================================
@bot.message_handler(func=lambda m: True)
def amount_handler(message):
    uid = str(message.from_user.id)
    user = config["users"].get(uid)

    if not user:
        return

    action = user.get("action")
    if not action:
        return

    if action.startswith("amount_"):
        try:
            amount = int(message.text)
        except:
            return bot.send_message(message.chat.id, "Faqat raqam kiriting!")

        if amount < 10000 or amount > 10000000:
            return bot.send_message(message.chat.id, "Noto‘g‘ri miqdor!")

        region = action.split("_")[1]
        pay = config["payments"][region]

        fee = random.randint(100, 500)
        total = amount + fee

        text = f"💵 To‘lov summasi: {amount}\n🔢 Kod: {fee}\n💰 Umumiy: {total}\n\n"

        if region == "uz":
            text += f"HUMO: {pay['humo']}\nUZCARD: {pay['uzcard']}"
        else:
            text += f"Telefon raqam: {pay['phone']}"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("To‘lov qildim", callback_data="proof"))

        bot.send_message(message.chat.id, text, reply_markup=markup)

        user["action"] = f"wait_{amount}"
        save_config(config)
        return


# =====================================================
# SCREENSHOT QABUL QILISH
# =====================================================
@bot.callback_query_handler(func=lambda c: c.data == "proof")
def send_proof(call):
    uid = str(call.from_user.id)
    config["users"][uid]["action"] = "send_proof"
    save_config(config)

    bot.send_message(call.message.chat.id, "To‘lov screenshotini yuboring:")


@bot.message_handler(content_types=['photo', 'document'])
def screenshot_handler(message):
    uid = str(message.from_user.id)
    user = config["users"][uid]

    if user["action"] != "send_proof":
        return

    user["action"] = None
    save_config(config)

    bot.send_message(message.chat.id, "😊 To‘lov adminga yuborildi. 5–10 daqiqada balans tushadi.")

    info = f"📥 Yangi to‘lov!\nID: {uid}\nUser: @{message.from_user.username}"

    bot.send_message(ADMIN, info)

    if message.photo:
        bot.send_photo(ADMIN, message.photo[-1].file_id)
    else:
        bot.send_document(ADMIN, message.document.file_id)


# =====================================================
# ADMIN PANEL
# =====================================================
@bot.message_handler(commands=['admin'])
def admin(message):
    if message.from_user.id != ADMIN:
        return

    menu = types.ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add("👥 Kanal sozlamalari", "💳 To‘lov kartalari")
    menu.add("🛒 Mahsulotlar", "👤 Balans o‘zgartirish")
    menu.add("◀️ Orqaga")
    bot.send_message(ADMIN, "Admin panel", reply_markup=menu)


# =====================================================
keep_alive()
bot.infinity_polling()