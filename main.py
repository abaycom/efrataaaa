import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest

# --- ኮንፊገሬሽን ---
TOKEN = "" 
ADMIN_ID = 5049565154

users = {}

def ensure_user(uid):
    if uid not in users:
        users[uid] = {"balance": 0, "selected_num": [], "bet": 0}

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 ወደ ዋና ማውጫ ተመለስ", callback_data="menu")]])

def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🎮 Play / መጫወት", callback_data="play")],
        [InlineKeyboardButton("💰 Deposit / መሙላት", callback_data="deposit")],
        [InlineKeyboardButton("💸 Withdraw / ማውጣት", callback_data="withdraw")],
        [InlineKeyboardButton("🏦 Balance / ሂሳብ", callback_data="balance")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ensure_user(uid)
    await update.effective_message.reply_text(
        "🎰 እንኳን ወደ Virtual Keno በሰላም መጡ!\nከታች ካሉት አማራጮች አንዱን ይምረጡ፦", 
        reply_markup=main_menu_keyboard()
    )

async def update_game_ui(update: Update, uid: int):
    keyboard = []
    for i in range(1, 81, 8):
        row = []
        for j in range(i, i + 8):
            label = f"✅{j}" if j in users[uid]['selected_num'] else str(j)
            row.append(InlineKeyboardButton(label, callback_data=f"num_{j}"))
        keyboard.append(row)
    
    keyboard.append([
        InlineKeyboardButton("🚀 Start Draw", callback_data="start_draw"),
        InlineKeyboardButton("🔙 Back / ተመለስ", callback_data="menu")
    ])
    
    text = (f"🎰 **Virtual Keno**\n\n"
            f"💰 Balance: {users[uid]['balance']} ብር\n"
            f"💸 Bet: {users[uid]['bet']} ብር\n"
            f"🎯 Selected ({len(users[uid]['selected_num'])}/10): {users[uid]['selected_num']}")
    
    try:
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.effective_message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except BadRequest:
        pass 

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    data = query.data
    await query.answer()
    ensure_user(uid)

    if data == "menu":
        context.user_data.clear()
        await query.edit_message_text("🏠 ዋና ማውጫ", reply_markup=main_menu_keyboard())
        return

    if data == "play":
        users[uid]['selected_num'] = [] 
        context.user_data["state"] = "AWAITING_BET"
        await query.edit_message_text("💵 የውርርድ መጠን ያስገቡ (Min 50 Birr)፦", reply_markup=back_kb())
        return

    if data.startswith("num_"):
        num = int(data.split("_")[1])
        if num in users[uid]['selected_num']:
            users[uid]['selected_num'].remove(num)
        elif len(users[uid]['selected_num']) < 10:
            users[uid]['selected_num'].append(num)
        await update_game_ui(update, uid)
        return

    if data == "start_draw":
        if not users[uid]['selected_num']:
            await query.message.reply_text("⚠️ እባክዎ ቁጥር ይምረጡ!", reply_markup=back_kb())
            return
        
        bet_amt = users[uid]['bet']
        users[uid]['balance'] -= bet_amt
        
        for i in range(5, 0, -1):
            await query.edit_message_text(f"⏳ ዕጣው ለመውጣት {i} ሰከንድ ቀርቷል...", reply_markup=back_kb())
            await asyncio.sleep(1)

        # --- ዝቅተኛ የማሸነፍ እድል (25% Chance) ---
        win_roll = random.randint(1, 100)
        if win_roll <= 25: 
            draw = sorted(random.sample(range(1, 81), 20))
        else:
            # ተጠቃሚው የመረጣቸውን ቁጥሮች ሆን ብሎ ማስቀረት
            pool = list(set(range(1, 81)) - set(users[uid]['selected_num']))
            draw = sorted(random.sample(pool, 20))

        matches = set(users[uid]['selected_num']).intersection(set(draw))
        count = len(matches)
        
        # --- ቀላል የሽልማት አሰላለፍ (Multiplier System) ---
        multipliers = {0: 0, 1: 1.5, 2: 3, 3: 8, 4: 20}
        multiplier = multipliers.get(count, 50 if count >= 5 else 0)
        
        prize = int(bet_amt * multiplier)
        users[uid]['balance'] += prize
        
        result = (f"🎰 **ውጤት**\n\n✅ የወጡት፦ `{draw}`\n"
                  f"🎯 የገጠሙ፦ {count}\n"
                  f"💰 ሽልማት፦ {prize} ብር\n"
                  f"💵 ቀሪ ሂሳብ፦ {users[uid]['balance']} ብር")
        
        users[uid]['selected_num'] = [] # Reset
        
        kb = [[InlineKeyboardButton("🎮 Play Again", callback_data="play")],
              [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")]]
        await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return

    if data.startswith("w_app_"):
        _, _, tid, amt = data.split("_")
        await context.bot.send_message(int(tid), f"✅ የ {amt} ብር ማውጫ ጥያቄዎ ጸድቋል!")
        await query.edit_message_text(f"✅ ክፍያ ለ {tid} ተፈጽሟል።")
        return

    if data == "withdraw":
        context.user_data["state"] = "AWAITING_WITHDRAW_AMT"
        await query.edit_message_text("💸 ማውጣት የሚፈልጉትን መጠን ይጻፉ፦", reply_markup=back_kb())
        return

    if data == "deposit":
        kb = [[InlineKeyboardButton("📱 Telebirr", callback_data="p_tele"), InlineKeyboardButton("🏦 CBE", callback_data="p_cbe")],
              [InlineKeyboardButton("🔙 ተመለስ", callback_data="menu")]]
        await query.edit_message_text("የክፍያ መንገድ ይምረጡ፦", reply_markup=InlineKeyboardMarkup(kb))
        return

    if data.startswith("p_"):
        context.user_data["state"] = "AWAITING_DEP_AMT"
        await query.edit_message_text("💰 መሙላት የሚፈልጉትን መጠን ይጻፉ፦", reply_markup=back_kb())
        return

    if data == "balance":
        await query.edit_message_text(f"🏦 ያሎት ቀሪ ሂሳብ፦ {users[uid]['balance']} ብር", reply_markup=main_menu_keyboard())
        return

    if data.startswith("adm_ok_"):
        _, _, tid, amt = data.split("_")
        users[int(tid)]['balance'] += int(amt)
        await context.bot.send_message(int(tid), f"✅ {amt} ብር ተጨምሯል!")
        await query.edit_message_caption("✅ ጸድቋል!")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    ensure_user(uid)
    state = context.user_data.get("state")

    if state == "AWAITING_BET" and text.isdigit():
        bet = int(text)
        if bet < 50:
            await update.message.reply_text("❌ ሚኒመም 50 ብር ነው።", reply_markup=back_kb())
            return
        if bet > users[uid]['balance']:
            await update.message.reply_text(f"❌ በቂ ሂሳብ የለዎትም (ቀሪ፦ {users[uid]['balance']} ብር)።", reply_markup=back_kb())
            return
        users[uid]["bet"] = bet
        context.user_data["state"] = None
        await update_game_ui(update, uid)

    elif state == "AWAITING_WITHDRAW_AMT" and text.isdigit():
        amt = int(text)
        if amt > users[uid]['balance']:
            await update.message.reply_text("❌ Insufficient balance.", reply_markup=back_kb())
        else:
            context.user_data["w_amt"] = amt
            context.user_data["state"] = "AWAITING_WITHDRAW_ACC"
            await update.message.reply_text(f"✅ {amt} ብር ለማውጣት አካውንት ይላኩ፦", reply_markup=back_kb())

    elif state == "AWAITING_WITHDRAW_ACC":
        amt = context.user_data.get("w_amt")
        users[uid]['balance'] -= amt
        kb = [[InlineKeyboardButton("✅ Approve", callback_data=f"w_app_{uid}_{amt}")]]
        await context.bot.send_message(ADMIN_ID, f"💸 **Withdraw Request**\nID: `{uid}`\nAmt: {amt}\nAcc: {text}", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("✅ ጥያቄዎ ደርሷል።", reply_markup=main_menu_keyboard())
        context.user_data.clear()

    elif state == "AWAITING_DEP_AMT" and text.isdigit():
        context.user_data.update({"temp_amt": text, "state": "AWAITING_PHOTO"})
        await update.message.reply_text(f"✅ {text} ብር ለመሙላት ፎቶ ይላኩ።", reply_markup=back_kb())

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if context.user_data.get("state") == "AWAITING_PHOTO":
        amt = context.user_data.get("temp_amt")
        kb = [[InlineKeyboardButton(f"✅ አጽድቅ ({amt})", callback_data=f"adm_ok_{uid}_{amt}")]]
        await context.bot.send_photo(ADMIN_ID, update.message.photo[-1].file_id, 
                                   caption=f"📩 ክፍያ ከ ID: `{uid}`\nመጠን: {amt}", reply_markup=InlineKeyboardMarkup(kb))
        await update.message.reply_text("✅ ተልኳል።", reply_markup=main_menu_keyboard())
        context.user_data["state"] = None

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.run_polling()
