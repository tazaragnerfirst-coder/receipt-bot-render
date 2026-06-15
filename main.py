import telebot
import psycopg2
import random
import string
from telebot import types
from datetime import datetime
import os
from flask import Flask
from threading import Thread

# --- Render እንዳያጠፋው የሚረዳ Web Server ---
app = Flask('')
@app.route('/')
def home(): return "I am alive!"

def run(): app.run(host='0.0.0.0', port=os.environ.get('PORT', 8080))
def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# --- ዋና ኮንፊገሬሽን ---
API_TOKEN = '8709046631:AAFk0Vvj5pz7KmokgxrQG4W-6IOVnkEjHik' # ያንተ ቦት ቶክን
DATABASE_URL = 'postgresql://neondb_owner:npg_kCFlTmsuwL37@ep-icy-water-atwln73j.c-9.us-east-1.aws.neon.tech/neondb?sslmode=require' # ደረጃ 1 ላይ ያገኘኸው
ADMIN_ID = 8397441795 

bot = telebot.TeleBot(API_TOKEN)
pending_receipts = {}

# (ትርጉሞች - ቀደም ሲል የነበሩት strings ዝርዝር እዚህ ጋር ይገባል...)
strings = {
    'am': {
        'welcome': "እንኳን ደህና መጡ! ቋንቋ ይምረጡ / Choose language:",
        'ask_name': "እባክዎ ሙሉ ስምዎን ይጻፉ፡",
        'pending': "ጥያቄዎ በአድሚን እየታየ ነው።",
        'ready': "ቦቱ ዝግጁ ነው። የደረሰኝ ቁጥር ይላኩ፡",
        'main_menu': ['ደረሰኝ መመዝገብ', 'ሁሉንም ሪፖርት እይ', 'የእኔ ሪፖርት'],
        'receipt_exists': "❌ ተመዝግቧል!\nቁጥር: {}\nመዝጋቢ: {}",
        'ask_amount': "✅ ቁጥር {} አዲስ ነው። መጠን ይምረጡ/ይጻፉ፡",
        'ask_bank': "ባንክ ይምረጡ፡",
        'confirm_text': "🔍 ያረጋግጡ፡\nቁጥር: {}\nመጠን: {}\nባንክ: {}",
        'btn_confirm': "✅ መዝግብ", 'btn_edit': "✏️ አስተካክል", 'btn_cancel': "Cancel",
        'success': "🎯 በስኬት ተመዝግቧል!", 'canceled': "ተሰርዟል።",
        'my_report': "📜 የእርስዎ ዝርዝር፡\n", 'total': "📊 ድምር፡ {} ብር", 'all_report': "📊 ማጠቃለያ፡\n"
    },
    'en': {
        'welcome': "Welcome! Please choose a language:",
        'ask_name': "Please enter your full name:",
        'pending': "Your request is pending admin approval.",
        'ready': "Bot is ready. Send receipt number:",
        'main_menu': ['Register Receipt', 'View All Reports', 'My Report'],
        'receipt_exists': "❌ Already Registered!\nNumber: {}\nBy: {}",
        'ask_amount': "✅ Number {} is new. Choose/Type amount:",
        'ask_bank': "Choose Bank:",
        'confirm_text': "🔍 Confirm Details:\nNumber: {}\nAmount: {}\nBank: {}",
        'btn_confirm': "✅ Confirm", 'btn_edit': "✏️ Edit", 'btn_cancel': "Cancel",
        'success': "🎯 Successfully Registered!", 'canceled': "Canceled.",
        'my_report': "📜 Your List:\n", 'total': "📊 Total: {} ETB", 'all_report': "📊 Summary:\n"
    }
}

# --- የዳታቤዝ ተግባራት (Postgres) ---
def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (user_id BIGINT PRIMARY KEY, full_name TEXT, status TEXT, lang TEXT)')
    cursor.execute('CREATE TABLE IF NOT EXISTS receipts (receipt_id TEXT PRIMARY KEY, amount TEXT, bank TEXT, created_at TEXT, added_by BIGINT)')
    cursor.execute("INSERT INTO users (user_id, full_name, status, lang) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id) DO NOTHING", (ADMIN_ID, 'Boss', 'APPROVED', 'am'))
    conn.commit()
    cursor.close()
    conn.close()

def get_user_info(user_id):
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("SELECT status, lang FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone(); cursor.close(); conn.close()
    return row if row else (None, 'am')

def get_main_menu(user_id, lang):
    m = strings[lang]['main_menu']
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if user_id == ADMIN_ID: markup.add(m[0], m[1], m[2])
    else: markup.add(m[0], m[2])
    return markup

# --- የቦቱ ሂደቶች (አጭር የተደረገ) ---

@bot.message_handler(commands=['start', 'cancel'])
def start(message):
    user_id = message.from_user.id
    status, lang = get_user_info(user_id)
    if not status:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("አማርኛ", callback_data="lang_am"), types.InlineKeyboardButton("English", callback_data="lang_en"))
        bot.send_message(user_id, strings['am']['welcome'], reply_markup=markup)
    elif status == 'APPROVED':
        bot.send_message(user_id, strings[lang]['ready'], reply_markup=get_main_menu(user_id, lang))
    else: bot.send_message(user_id, strings[lang]['pending'])

@bot.callback_query_handler(func=lambda call: call.data.startswith('lang_'))
def set_lang(call):
    lang = call.data.split('_')[1]; user_id = call.from_user.id
    conn = get_db(); cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, status, lang) VALUES (%s, %s, %s) ON CONFLICT (user_id) DO UPDATE SET lang = %s", (user_id, 'NEW', lang, lang))
    conn.commit(); cursor.close(); conn.close()
    bot.edit_message_text(strings[lang]['ask_name'], user_id, call.message.message_id)
    bot.register_next_step_handler(call.message, request_access, lang)

def request_access(message, lang):
    name = message.text; uid = message.from_user.id
    conn = get_db(); cur = conn.cursor()
    cur.execute("UPDATE users SET full_name = %s, status = 'PENDING' WHERE user_id = %s", (name, uid))
    conn.commit(); cur.close(); conn.close()
    bot.send_message(uid, strings[lang]['pending'])
    mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton("Approve", callback_data=f"user_app_{uid}"), types.InlineKeyboardButton("Reject", callback_data=f"user_rej_{uid}"))
    bot.send_message(ADMIN_ID, f"New User: {name}\nID: {uid}", reply_markup=mk)

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    uid = message.from_user.id; status, lang = get_user_info(uid)
    if status != 'APPROVED': return
    text = message.text; s = strings[lang]

    if text in [s['main_menu'][1], 'View All Reports'] and uid == ADMIN_ID:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT u.full_name, COUNT(r.receipt_id), SUM(CASE WHEN r.amount ~ '^[0-9]+$' THEN CAST(r.amount AS INTEGER) ELSE 0 END) FROM users u LEFT JOIN receipts r ON u.user_id = r.added_by GROUP BY u.full_name")
        reps = cur.fetchall(); cur.close(); conn.close()
        msg = s['all_report']
        for r in reps: msg += f"👤 {r[0]}: {r[1]} (Sum: {r[2] if r[2] else 0})\n"
        bot.send_message(uid, msg, reply_markup=get_main_menu(uid, lang)); return

    if text in [s['main_menu'][2], 'My Report']:
        conn = get_db(); cur = conn.cursor()
        cur.execute("SELECT receipt_id, amount, bank FROM receipts WHERE added_by = %s", (uid,))
        data = cur.fetchall(); cur.close(); conn.close()
        msg = s['my_report']; total = sum(int(r[1]) for r in data if r[1].isdigit())
        for r in data: msg += f"🔢 {r[0]} | 💰 {r[1]} | 🏦 {r[2]}\n"
        bot.send_message(uid, msg + s['total'].format(total), reply_markup=get_main_menu(uid, lang)); return

    rid = text.strip()
    if rid == 'Cancel' or text in s['main_menu']: return
    conn = get_db(); cur = conn.cursor()
    cur.execute("SELECT receipt_id, added_by FROM receipts WHERE receipt_id = %s", (rid,))
    data = cur.fetchone()
    if data:
        cur.execute("SELECT full_name FROM users WHERE user_id = %s", (data[1],))
        name = cur.fetchone()[0]; cur.close(); conn.close()
        bot.reply_to(message, s['receipt_exists'].format(rid, name))
    else:
        cur.close(); conn.close()
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
        markup.add(*[types.KeyboardButton(str(a)) for a in [50,100,200,300,400,500,600,700,800,900,1000]])
        markup.row('Cancel')
        msg = bot.send_message(uid, s['ask_amount'].format(rid), reply_markup=markup)
        bot.register_next_step_handler(msg, process_amount, rid, lang)

def process_amount(message, rid, lang):
    if message.text == 'Cancel': bot.send_message(message.chat.id, strings[lang]['canceled'], reply_markup=get_main_menu(message.from_user.id, lang)); return
    amt = message.text.strip(); mk = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    mk.add('Telebirr', 'CBE', 'Cancel')
    msg = bot.send_message(message.chat.id, strings[lang]['ask_bank'], reply_markup=mk)
    bot.register_next_step_handler(msg, show_confirm, rid, amt, lang)

def show_confirm(message, rid, amt, lang):
    if message.text == 'Cancel': bot.send_message(message.chat.id, strings[lang]['canceled'], reply_markup=get_main_menu(message.from_user.id, lang)); return
    bnk = message.text.strip(); uid = message.from_user.id
    pending_receipts[uid] = {'id': rid, 'amount': amt, 'bank': bnk}
    s = strings[lang]; mk = types.InlineKeyboardMarkup()
    mk.add(types.InlineKeyboardButton(s['btn_confirm'], callback_data="rec_confirm"), types.InlineKeyboardButton(s['btn_edit'], callback_data="rec_edit"), types.InlineKeyboardButton(s['btn_cancel'], callback_data="rec_cancel"))
    bot.send_message(uid, s['confirm_text'].format(rid, amt, bnk), reply_markup=mk)

@bot.callback_query_handler(func=lambda call: True)
def callbacks(call):
    uid = call.from_user.id
    if call.data.startswith('user_'):
        act, tid = call.data.split('_')[1], int(call.data.split('_')[2])
        conn = get_db(); cur = conn.cursor()
        if act == 'app':
            cur.execute("UPDATE users SET status = 'APPROVED' WHERE user_id = %s", (tid,))
            bot.send_message(tid, "APPROVED! Type /start")
        else: cur.execute("DELETE FROM users WHERE user_id = %s", (tid,))
        conn.commit(); cur.close(); conn.close()
        bot.delete_message(call.message.chat.id, call.message.message_id); return

    _, lang = get_user_info(uid)
    if uid not in pending_receipts: return
    d = pending_receipts[uid]
    if call.data == "rec_confirm":
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        conn = get_db(); cur = conn.cursor()
        cur.execute("INSERT INTO receipts (receipt_id, amount, bank, created_at, added_by) VALUES (%s, %s, %s, %s, %s)", (d['id'], d['amount'], d['bank'], now, uid))
        conn.commit(); cur.close(); conn.close()
        bot.edit_message_text(strings[lang]['success'], uid, call.message.message_id)
        bot.send_message(uid, strings[lang]['ready'], reply_markup=get_main_menu(uid, lang))
        del pending_receipts[uid]
    elif call.data == "rec_cancel":
        del pending_receipts[uid]
        bot.edit_message_text(strings[lang]['canceled'], uid, call.message.message_id)
        bot.send_message(uid, strings[lang]['ready'], reply_markup=get_main_menu(uid, lang))

if __name__ == "__main__":
    init_db()
    keep_alive()
    bot.polling(none_stop=True)
