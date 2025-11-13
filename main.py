import telebot
from telebot import types
import json, os, random
from keep_alive import keep_alive

keep_alive()  # Botni 24/7 ishlash uchun

# --- CONFIG ---
with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

BOT_TOKEN = config["bot_token"]
ADMIN_ID = config["owner_id"]
MANDATORY_CHANNEL = config["mandatory_channel"]

bot = telebot.TeleBot(BOT_TOKEN)

# --- DATA FILES ---
USERS_FILE = "users.json"
PAYMENTS_FILE = "payments.json"

if not os.path.exists(USERS_FILE):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump({}, f)
if not os.path.exists(PAYMENTS_FILE):
    with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)

def load_users():
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def load_payments():
    with open(PAYMENTS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_payments(payments):
    with open(PAYMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(payments, f, ensure_ascii=False, indent=2)

# --- START ---
@bot.message_handler(commands=["start"])
def start(message):
    user_id = str(message.from_user.id)
    try:
        chat_member = bot.get_chat_member(MANDATORY_CHANNEL, message.from_user.id)
        if chat_member.status in ["left", "kicked"]:
            bot.send_message(message.chat.id,
                             f"❌ Iltimos, kanalga obuna bo‘ling: {MANDATORY_CHANNEL}")
            return
    except:
        bot.send_message(message.chat.id,
                         f"❌ Kanalga obuna tekshirilmadi, keyinroq urinib ko‘ring: {MANDATORY_CHANNEL}")
        return

    users = load_users()
    if user_id not in users:
        users[user_id] = {"username": message.from_user.username, "balance": 0, "transactions": []}
        save_users(users)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for item in config["shop_menu"]:
        if item["enabled"]:
            markup.add(types.KeyboardButton(item["name"]))
    if config["support_button"]["enabled"]:
        markup.add(types.KeyboardButton(config["support_button"]["text"]))

    bot.send_message(message.chat.id,
                     f"Assalomu alaykum, {message.from_user.first_name}! Asosiy menyu:",
                     reply_markup=markup)

# --- MESSAGE HANDLER ---
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    user_id = str(message.from_user.id)
    text = message.text
    users = load_users()

    # Admin bilan bog‘lanish
    if text == config["support_button"]["text"]:
        bot.send_message(message.chat.id, config["support_button"]["auto_reply"])
        bot.send_message(ADMIN_ID,
                         f"📩 Yordam so‘rovi:\nFrom: @{message.from_user.username} ({user_id})")
        return

    # Sotib olish
    shop_item = next((i for i in config["shop_menu"] if i["name"] == text and i["enabled"]), None)
    if shop_item:
        if users[user_id]["balance"] < shop_item.get("price", 0):
            bot.send_message(message.chat.id, "⚠ Hisobingizda mablag‘ yetarli emas!")
            return
        msg = bot.send_message(message.chat.id, f"{shop_item['name']} sotib olish uchun PUBG ID kiriting:")
        bot.register_next_step_handler(msg, purchase_process, shop_item)
        return

    # To‘lov tizimini tanlash
    if text in ["HUMO", "UZCARD", "Rossiya / Qozog‘iston"]:
        if text == "HUMO":
            card = config["cards"]["HUMO"]
            bot.send_message(message.chat.id, f"💳 HUMO: {card['number']} ({card['owner']}) ga to‘lov qiling")
        elif text == "UZCARD":
            card = config["cards"]["UZCARD"]
            bot.send_message(message.chat.id, f"💳 UZCARD: {card['number']} ({card['owner']}) ga to‘lov qiling")
        else:
            phone = config["phone_payments"]["RUSSIA_KZ"]
            bot.send_message(message.chat.id, f"📞 Telefon orqali to‘lov: {phone}")

        msg = bot.send_message(message.chat.id, "✅ To‘lov qilganingizdan so‘ng 'To‘lov qildim' tugmasini bosing va fayl yuboring")
        bot.register_next_step_handler(msg, upload_screenshot)
        return

# --- PURCHASE PROCESS ---
def purchase_process(message, shop_item):
    user_id = str(message.from_user.id)
    users = load_users()
    pubg_id = message.text.strip()
    price = shop_item.get("price", 0)

    users[user_id]["balance"] -= price
    users[user_id]["transactions"].append({
        "type": "purchase",
        "item": shop_item["name"],
        "amount": price,
        "pubg_id": pubg_id,
        "status": "completed"
    })
    save_users(users)

    bot.send_message(ADMIN_ID,
                     f"🛒 Sotib olish:\nUser: @{message.from_user.username} ({user_id})\nItem: {shop_item['name']}\nPrice: {price}\nPUBG ID: {pubg_id}")

    bot.send_message(message.chat.id, f"✅ {shop_item['name']} hisobingizga tushdi!\nPUBG ID: {pubg_id}")

# --- UPLOAD SCREENSHOT ---
def upload_screenshot(message):
    user_id = str(message.from_user.id)
    if not message.document and not message.photo:
        bot.send_message(message.chat.id, "❌ Iltimos, skrenshot yoki fayl yuboring")
        return

    os.makedirs("payments", exist_ok=True)

    if message.document:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = f"payments/{user_id}_{message.document.file_name}"
        with open(file_name, "wb") as f:
            f.write(downloaded_file)
    elif message.photo:
        file_info = bot.get_file(message.photo[-1].file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_name = f"payments/{user_id}_photo.jpg"
        with open(file_name, "wb") as f:
            f.write(downloaded_file)

    payments = load_payments()
    payments.append({"user_id": user_id, "file": file_name, "status": "pending"})
    save_payments(payments)

    bot.send_message(message.chat.id, "✅ Xabaringiz adminga yuborildi. Tez orada hisobingizga pul tushadi")
    bot.send_message(ADMIN_ID, f"📩 Yangi to‘lov fayli:\nUser: @{message.from_user.username} ({user_id})\nFayl: {file_name}")

# --- POLLING ---
bot.polling(none_stop=True)