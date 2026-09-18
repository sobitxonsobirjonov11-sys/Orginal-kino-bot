import sqlite3
import telebot
from telebot import types

# ================= SOZLAMALAR =================
TOKEN = "8847812245:AAFn2qctTXM_pE-V-W6VVbhnGaxaNfW0tk0"
ADMIN_ID = 8274938812          # O'z ID raqamingizni yozing
GROUP_ID = -1004421904831     # Maxfiy guruh ID-si (bot admin bo'lishi shart)
DB_PATH = 'kino_baza.db'

bot = telebot.TeleBot(TOKEN, parse_mode="HTML")

# ================= BAZA SOZLAMALARI =================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS movies
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, part INTEGER, file_id TEXT, size REAL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (user_id INTEGER PRIMARY KEY, full_name TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS channels
                      (id INTEGER PRIMARY KEY AUTOINCREMENT, channel_id TEXT UNIQUE, channel_url TEXT, title TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id, full_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, full_name) VALUES (?, ?)", (user_id, full_name))
    conn.commit()
    conn.close()

# ================= MAJBURIY OBUNA TEKSHIRUVI =================
def check_sub(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT channel_id, channel_url, title FROM channels")
    channels = cursor.fetchall()
    conn.close()

    unsubscribed = []
    for ch_id, ch_url, title in channels:
        try:
            member = bot.get_chat_member(chat_id=ch_id, user_id=user_id)
            if member.status in ['left', 'kicked']:
                unsubscribed.append((ch_url, title))
        except Exception:
            pass
    return unsubscribed

def get_sub_keyboard(unsubscribed_channels):
    markup = types.InlineKeyboardMarkup(row_width=1)
    for ch_url, title in unsubscribed_channels:
        markup.add(types.InlineKeyboardButton(text=f"📢 {title}", url=ch_url))
    markup.add(types.InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_subscription"))
    return markup

# ================= 1. ADMIN PANEL VA STATISTIKA =================

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if message.from_user.id != ADMIN_ID:
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add("📊 Statistika", "➕ Kanal qo'shish", "📋 Kanallar ro'yxati")
    bot.send_message(message.chat.id, "👑 <b>Admin paneliga xush kelibsiz!</b>", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "📊 Statistika")
def show_stats(message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM movies")
    movies_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM channels")
    channels_count = cursor.fetchone()[0]
    conn.close()

    text = (f"📊 <b>Bot Statistikasi:</b>\n\n"
            f"👤 Foydalanuvchilar: <b>{users_count} ta</b>\n"
            f"🎬 Kinolar soni: <b>{movies_count} ta</b>\n"
            f"📢 Majburiy kanallar: <b>{channels_count} ta</b>")
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "➕ Kanal qo'shish")
def start_add_channel(message):
    text = ("📢 <b>Kanal qo'shish uchun ma'lumotni quyidagi formatda yuboring:</b>\n\n"
            "<code>KANAL_ID KANAL_LINK KANAL_NOMI</code>\n\n"
            "<b>Masalan:</b>\n"
            "<code>@mychannel https://t.me/mychannel Mening Kanalim</code>\n"
            "yoki ID bilan:\n"
            "<code>-100123456789 https://t.me/mychannel Mening Kanalim</code>\n\n"
            "⚠️ <i>Eslatma: Bot o'sha kanalda ADMIN bo'lishi shart!</i>")
    msg = bot.send_message(message.chat.id, text)
    bot.register_next_step_handler(msg, process_add_channel)

def process_add_channel(message):
    parts = message.text.split(maxsplit=2)
    if len(parts) < 3:
        return bot.reply_to(message, "❌ Xato format! Ma'lumotlarni to'liq yuboring.\nFormat: <code>KANAL_ID LINK NOMI</code>")

    ch_id, ch_url, title = parts[0], parts[1], parts[2]

    try:
        bot.get_chat_member(chat_id=ch_id, user_id=bot.get_me().id)
    except Exception as e:
        return bot.reply_to(message, f"❌ Bot ko'rsatilgan kanalda admin emas yoki Kanal ID noto'g'ri!\nXatolik: {e}")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO channels (channel_id, channel_url, title) VALUES (?, ?, ?)",
                   (ch_id, ch_url, title))
    conn.commit()
    conn.close()

    bot.reply_to(message, f"✅ <b>{title}</b> kanali majburiy obuna ro'yxatiga qo'shildi!")

@bot.message_handler(func=lambda msg: msg.from_user.id == ADMIN_ID and msg.text == "📋 Kanallar ro'yxati")
def list_channels(message):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, channel_id FROM channels")
    channels = cursor.fetchall()
    conn.close()

    if not channels:
        return bot.send_message(message.chat.id, "📢 Hozircha majburiy kanallar yo'q.")

    markup = types.InlineKeyboardMarkup(row_width=1)
    for c_id, title, ch_id in channels:
        markup.add(types.InlineKeyboardButton(text=f"🗑 {title} ({ch_id})", callback_data=f"del_chan:{c_id}"))

    bot.send_message(message.chat.id, "📋 <b>Majburiy kanallar ro'yxati:</b>\n(O'chirish uchun ustiga bosing)", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('del_chan:'))
def delete_channel(call):
    if call.from_user.id != ADMIN_ID:
        return
    c_id = call.data.split(':')[1]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM channels WHERE id = ?", (c_id,))
    conn.commit()
    conn.close()

    bot.answer_callback_query(call.id, "🗑 Kanal o'chirildi!", show_alert=True)
    bot.delete_message(call.message.chat.id, call.message.message_id)

# ================= 2. ADMIN: KINO QO'SHISH VA O'CHIRISH =================

@bot.message_handler(content_types=['video'])
def start_add_movie(message):
    if message.from_user.id != ADMIN_ID:
        return
    file_id = message.video.file_id
    size_mb = (message.video.file_size / (1024 * 1024)) if message.video.file_size else 0

    msg = bot.reply_to(message, "🎬 Video qabul qilindi.\n\nIltimos, kino nomini yozing (Masalan: <i>Forsaj</i>):")
    bot.register_next_step_handler(msg, get_movie_name, file_id, size_mb)

def get_movie_name(message, file_id, size_mb):
    movie_name = message.text.strip()
    msg = bot.reply_to(message, f"🔢 <b>{movie_name}</b> - ajoyib.\nEndi qismini yozing (Faqat raqam, masalan: <i>1</i>):")
    bot.register_next_step_handler(msg, get_movie_part, file_id, size_mb, movie_name)

def get_movie_part(message, file_id, size_mb, movie_name):
    if not message.text.isdigit():
        return bot.reply_to(message, "❌ Iltimos, qismni faqat raqamda yozing!")

    m_part = int(message.text)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO movies (name, part, file_id, size) VALUES (?, ?, ?, ?)",
                   (movie_name, m_part, file_id, size_mb))
    conn.commit()
    conn.close()

    try:
        bot.send_video(GROUP_ID, file_id, caption=f" 📦 Baza: <b>{movie_name}</b> | {m_part}-qism")
        group_status = "Guruhga yuborildi."
    except Exception as e:
        group_status = f"Guruhga ketmadi: {e}"

    bot.reply_to(message, f"✅ Tayyor!\n<b>{movie_name}</b> ({m_part}-qism, {round(size_mb, 1)} MB) bazaga qo'shildi.\n{group_status}")

@bot.message_handler(commands=['del'])
def delete_movie_cmd(message):
    if message.from_user.id != ADMIN_ID:
        return
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        return bot.reply_to(message, "Kino ID raqamini yozing. Masalan: /del 5")

    m_id = int(args[1])
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM movies WHERE id = ?", (m_id,))
    conn.commit()
    conn.close()

    bot.reply_to(message, "🗑 Kino bazadan o'chirildi.")

# ================= 3. USER: MENYU VA OBUNA TEKSHIRUVI =================

@bot.message_handler(commands=['start'])
def start_handler(message):
    add_user(message.from_user.id, message.from_user.full_name)

    unsubscribed = check_sub(message.from_user.id)
    if unsubscribed:
        return bot.send_message(message.chat.id, "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:</b>",
                               reply_markup=get_sub_keyboard(unsubscribed))

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT name FROM movies")
    movies = cursor.fetchall()
    conn.close()

    if not movies:
        return bot.send_message(message.chat.id, "🎬 Hozircha bazada kinolar yo'q.")

    markup = types.InlineKeyboardMarkup(row_width=2)
    for movie in movies:
        markup.add(types.InlineKeyboardButton(text=f"🎬 {movie[0]}", callback_data=f"list:{movie[0][:40]}"))

    bot.send_message(message.chat.id, "<b>Assalomu alaykum!</b>\nKo'rmoqchi bo'lgan kinongizni tanlang:", reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data == "check_subscription")
def check_sub_callback(call):
    unsubscribed = check_sub(call.from_user.id)
    if unsubscribed:
        bot.answer_callback_query(call.id, "❌ Siz hali barcha kanallarga obuna bo'lmadingiz!", show_alert=True)
    else:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        start_handler(call.message)

@bot.callback_query_handler(func=lambda c: c.data.startswith('list:'))
def list_parts(call):
    unsubscribed = check_sub(call.from_user.id)
    if unsubscribed:
        return bot.send_message(call.message.chat.id, "⚠️ Botdan foydalanish uchun kanallarga obuna bo'ling:",
                                reply_markup=get_sub_keyboard(unsubscribed))

    movie_name = call.data.split(':', 1)[1]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, part FROM movies WHERE name LIKE ? ORDER BY part", (f"{movie_name}%",))
    parts = cursor.fetchall()
    conn.close()

    markup = types.InlineKeyboardMarkup(row_width=1)
    for m_id, p_num in parts:
        markup.add(types.InlineKeyboardButton(text=f"📥 {p_num}-qismni yuklash", callback_data=f"get:{m_id}"))

    markup.add(types.InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_main"))

    try:
        bot.edit_message_text(f"🎥 <b>{movie_name}</b>\nQismlarni tanlang:",
                              chat_id=call.message.chat.id,
                              message_id=call.message.message_id,
                              reply_markup=markup)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "back_to_main")
def back_to_main(call):
    bot.delete_message(call.message.chat.id, call.message.message_id)
    start_handler(call.message)

# ================= 4. USER: YUKLASH VA HAJM NAZORATI =================

@bot.callback_query_handler(func=lambda c: c.data.startswith('get:'))
def check_size_and_send(call):
    unsubscribed = check_sub(call.from_user.id)
    if unsubscribed:
        return bot.send_message(call.message.chat.id, "⚠️ Botdan foydalanish uchun kanallarga obuna bo'ling:",
                                reply_markup=get_sub_keyboard(unsubscribed))

    m_id = call.data.split(':')[1]

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, name, part, size FROM movies WHERE id=?", (m_id,))
    res = cursor.fetchone()
    conn.close()

    if res:
        f_id, name, part, size = res
        if size and size > 100:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("✅ Ha, yuboravering", callback_data=f"force_get:{m_id}"))
            markup.add(types.InlineKeyboardButton("❌ Yo'q, keyinroq", callback_data="back_to_main"))

            bot.send_message(
                call.message.chat.id,
                f"⚠️ <b>Diqqat!</b>\nBu kinoning hajmi <b>{round(size, 1)} MB</b>. Trafikingiz ko'p ketmasligi uchun <b>Wi-Fi</b> tarmog'iga ulanganda yuklab olishni maslahat beramiz.\n\nShunga qaramay, sizga yuboraymi?",
                reply_markup=markup
            )
            bot.answer_callback_query(call.id)
        else:
            bot.send_video(call.from_user.id, f_id, caption=f"🎬 <b>{name}</b> | {part}-qism")
            bot.answer_callback_query(call.id, "Yuborilmoqda...")
    else:
        bot.answer_callback_query(call.id, "Kino topilmadi", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith('force_get:'))
def force_send(call):
    m_id = call.data.split(':')[1]
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, name, part FROM movies WHERE id=?", (m_id,))
    res = cursor.fetchone()
    conn.close()

    if res:
        bot.send_video(call.from_user.id, res[0], caption=f"🎬 <b>{res[1]}</b> | {res[2]}-qism")
        bot.delete_message(call.message.chat.id, call.message.message_id)
    bot.answer_callback_query(call.id)

# ================= 5. SO'ROV YUBORISH =================

@bot.message_handler(content_types=['text'])
def user_request(message):
    if message.text.startswith('/'):
        return
    add_user(message.from_user.id, message.from_user.full_name)

    bot.send_message(message.chat.id, "🔍 Bu kino yoki matn hozircha bazamizda yo'q. Sizning xabaringiz adminga yetkazildi!")
    bot.send_message(ADMIN_ID, f"❓ <b>Yangi so'rov/xabar:</b>\n👤 User: {message.from_user.full_name}\n💬 Matn: {message.text}")

# ================= ISHGA TUSHIRISH =================
if __name__ == '__main__':
    init_db()
    print("Bot ishga tushdi...")
    bot.infinity_polling(skip_pending=True)
