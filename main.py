import random
import asyncio
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest

# --- ኮንፊገሬሽን ---
TOKEN = "" 
ADMIN_ID = 5049565154
BOT_USERNAME = "Hiaiethiopiabot" # <--- የቦትህን Username እዚህ ይተኩ
TELEBIRR_ACC = "09090909"
DATA_FILE = "users_db.json"

# --- የዳታ አያያዝ ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f)

users = load_data()

def ensure_user(uid):
    uid_str = str(uid)
    if uid_str not in users:
        users[uid_str] = {"balance": 50, "selected_num": [], "bet": 0}
        save_data()

# --- ሜኑዎች ---
def main_menu():
    keyboard = [
        [InlineKeyboardButton("🎮 Play / መጫወት", callback_data="play")],
        [InlineKeyboardButton("💰 Deposit / መሙላት", callback_data="deposit")],
        [InlineKeyboardButton("💸 Withdraw / ማውጣት", callback_data="withdraw")],
        [InlineKeyboardButton("🏦 Balance / ሂሳብ", callback_data="balance")],
        [InlineKeyboardButton("🎁 Invite / ጋብዝ", callback_data="invite")]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- ዋና ተግባራት ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    uid_str = str(uid)
    ensure_user(uid)
    
    if context.args and uid_str not in users:
        ref_id = str(context.args[0])
        if ref_id in users and ref_id != uid_str:
            users[ref_id]["balance"] += 10
            save_data()
            try: await context.bot.send_message(int(ref_id), "🎉 በሪፈራል ሊንክዎ ሰው ስለገባ 10 ብር ተሸልመዋል!")
            except: pass

    await update.effective_message.reply_text("🎰 እንኳን ወደ Virtual Keno በሰላም መጡ!", reply_markup=main_menu())

async def update_game_ui(update: Update, uid: int):
    uid_str = str(uid)
    keyboard = []
    for i in range(1, 81, 8):
        row = [InlineKeyboardButton(f"✅{j}" if j in users[uid_str]['selected_num'] else str(j), callback_data=f"num_{j}") for j in range(i, i + 8)]
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("🚀 ዕጣውን ጀምር (Start)", callback_data="start_draw")])
    keyboard.append([InlineKeyboardButton("🔙 ተመለስ", callback_data="menu")])
    
    text = (f"🎰 **Virtual Keno**\n\n💰 ሂሳብ: {users[uid_str]['balance']} ብር\n"
            f"💸 ውርርድ: {users[uid_str]['bet']} ብር\n🎯 የመረጧቸው: {users[uid_str]['selected_num']}")
    
    # AttributeError: 'NoneType' object has no attribute 'edit_message_text' ለመከላከል የተደረገ ማስተካከያ
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except Exception: pass

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    uid_str = str(uid)
    data = query.data
    ensure_user(uid)
    await query.answer()

    if data == "menu":
        context.user_data.clear()
        await query.edit_message_text("🏠 ዋና ማውጫ", reply_markup=main_menu())

    elif data == "play":
        users[uid_str]['selected_num'] = []
        context.user_data["state"] = "BET"
        await query.edit_message_text("💵 መወራረድ የሚፈልጉትን መጠን ያስገቡ (Min 10)፦", 
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ተመለስ", callback_data="menu")]]))

    elif data.startswith("num_"):
        num = int(data.split("_")[1])
        if num in users[uid_str]['selected_num']: users[uid_str]['selected_num'].remove(num)
        elif len(users[uid_str]['selected_num']) < 10: users[uid_str]['selected_num'].append(num)
        await update_game_ui(update, uid)

    elif data == "start_draw":
        if not users[uid_str]['selected_num']:
            await query.message.reply_text("⚠️ እባክዎ ቁጥር ይምረጡ!")
            return
        
        # 10 ሰከንድ ቆጠራ
        for i in range(10, 0, -1):
            try:
                await query.edit_message_text(f"⏳ ዕጣው ለመውጣት {i} ሰከንድ ቀርቷል...")
                await asyncio.sleep(1)
            except: continue

        win = random.randint(1, 100) <= 30
        draw = sorted(random.sample(range(1, 81), 20)) if win else sorted(random.sample(list(set(range(1, 81)) - set(users[uid_str]['selected_num'])), 20))
        matches = set(users[uid_str]['selected_num']).intersection(set(draw))
        
        prize = int((users[uid_str]['bet'] * 10 * len(matches)) / len(users[uid_str]['selected_num'])) if matches else 0
        users[uid_str]['balance'] += prize
        save_data()
        
        res = f"🎰 **ውጤት**\n\n✅ የወጡት፦ `{draw}`\n🎯 የገጠሙ፦ {len(matches)}\n💰 ሽልማት፦ {prize} ብር\n💵 ቀሪ፦ {users[uid_str]['balance']} ብር"
        await query.edit_message_text(res, reply_markup=main_menu(), parse_mode='Markdown')

    elif data == "deposit":
        context.user_data["state"] = "DEP_AMT"
        await query.edit_message_text(f"💰 በ Telebirr መሙላት የሚፈልጉትን መጠን ይጻፉ፦\n(Account: {TELEBIRR_ACC})", 
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ተመለስ", callback_data="menu")]]))

    elif data == "withdraw":
        context.user_data["state"] = "W_AMT"
        await query.edit_message_text("💸 ማውጣት የሚፈልጉትን መጠን ይጻፉ፦", 
                                     reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ተመለስ", callback_data="menu")]]))

    elif data == "balance":
        await query.edit_message_text(f"🏦 ያሎት ቀሪ ሂሳብ፦ {users[uid_str]['balance']} ብር", reply_markup=main_menu())

    elif data == "invite":
        link = f"https://t.me/{BOT_USERNAME}?start={uid}"
        await query.edit_message_text(f"🎁 መጋበዣ ሊንክዎ፦\n`{link}`\n\nበዚህ ሊንክ ለሚገባ ሰው 10 ብር ያገኛሉ።", 
                                     parse_mode='Markdown', reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ተመለስ", callback_data="menu")]]))

    elif data.startswith("app_d_"):
        _, _, tid, amt = data.split("_")
        users[str(tid)]["balance"] += int(amt)
        save_data()
        await context.bot.send_message(int(tid), f"✅ የ {amt} ብር ክፍያዎ ጸድቆ ሂሳብዎ ላይ ተጨምሯል!")
        await query.edit_message_text(f"✅ ክፍያ ለ ID {tid} ጸድቋል።")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    uid_str = str(uid)
    text = update.message.text
    state = context.user_data.get("state")
    ensure_user(uid)

    if state == "BET" and text.isdigit():
        amt = int(text)
        if 10 <= amt <= users[uid_str]['balance']:
            users[uid_str]['bet'] = amt
            users[uid_str]['balance'] -= amt
            save_data()
            context.user_data["state"] = None
            await update_game_ui(update, uid)
        else: await update.message.reply_text("❌ በቂ ሂሳብ የለዎትም ወይም ሚኒመም 10 ብር ነው።")

    elif state == "DEP_AMT" and text.isdigit():
        context.user_data.update({"d_amt": text, "state": "DEP_PHOTO"})
        await update.message.reply_text(f"✅ {text} ብር ወደ {TELEBIRR_ACC} ከላኩ በኋላ የደረሰኝ ፎቶ (Screenshot) ይላኩ።")

    elif state == "W_AMT" and text.isdigit():
        amt = int(text)
        if amt <= users[uid_str]['balance']:
            context.user_data.update({"w_amt": amt, "state": "W_ACC"})
            await update.message.reply_text("✅ ገንዘቡ እንዲላክበት የሚፈልጉትን ስልክ ቁጥር ያስገቡ፦")
        else: await update.message.reply_text("❌ በቂ ሂሳብ የለዎትም።")

    elif state == "W_ACC":
        amt = context.user_data["w_amt"]
        users[uid_str]['balance'] -= amt
        save_data()
        await context.bot.send_message(ADMIN_ID, f"💸 **ወጪ ጥያቄ**\nID: `{uid}`\nመጠን: {amt}\nአካውንት: {text}")
        await update.message.reply_text("✅ ጥያቄዎ ተልኳል! አድሚን ሲያጸድቀው ይላክለዎታል።", reply_markup=main_menu())
        context.user_data.clear()

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") == "DEP_PHOTO":
        amt = context.user_data["d_amt"]
        uid = update.effective_user.id
        kb = [[InlineKeyboardButton(f"✅ አጽድቅ ({amt} ብር)", callback_data=f"app_d_{uid}_{amt}")]]
        await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, 
                                   caption=f"📩 **ክፍያ ጥያቄ**\nID: `{uid}`\nመጠን: {amt} ብር", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("✅ የደረሰኝ ፎቶው ተልኳል! አድሚን እስኪያጸድቅ ድረስ ይጠብቁ።", reply_markup=main_menu())
        context.user_data.clear()

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    print("🚀 ቦቱ በትክክል ተጀምሯል...")
    app.run_polling()
