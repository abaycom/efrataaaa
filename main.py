import random
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest

# --- ኮንፊገሬሽን ---
TOKEN = "YOUR_BOT_TOKEN" 
ADMIN_ID = 5049565154 

users = {}

def ensure_user(uid):
    if uid not in users:
        # ለጀማሪ 50 ብር ቦነስ እዚህ ጋር ተጨምሯል
        users[uid] = {"balance": 50, "selected_num": [], "bet": 0}

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
    is_new = uid not in users
    ensure_user(uid)
    
    msg = "🎰 እንኳን ወደ Virtual Keno በሰላም መጡ!"
    if is_new:
        msg += "\n\n🎁 ለጀማሪነት የ **50 ብር** ስጦታ ተበርክቶልዎታል! አሁኑኑ መጫወት ይጀምሩ።"
        
    await update.effective_message.reply_text(msg, reply_markup=main_menu_keyboard())

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
        await query.edit_message_text("💵 የውርርድ መጠን ያስገቡ (Min 10 Birr)፦", reply_markup=back_kb())
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
        selected_count = len(users[uid]['selected_num'])
        if selected_count == 0:
            await query.message.reply_text("⚠️ እባክዎ ቁጥር ይምረጡ!", reply_markup=back_kb())
            return
        
        bet_amt = users[uid]['bet']
        if users[uid]['balance'] < bet_amt:
             await query.message.reply_text("❌ በቂ ሂሳብ የለዎትም!", reply_markup=back_kb())
             return

        users[uid]['balance'] -= bet_amt
        
        # --- 10 ሰከንድ የቆጠራ ጊዜ ---
        for i in range(10, 0, -1):
            try:
                await query.edit_message_text(f"⏳ ዕጣው ለመውጣት {i} ሰከንድ ቀርቷል...\n🍀 መልካም ዕድል!", reply_markup=back_kb())
                await asyncio.sleep(1)
            except BadRequest: continue

        # --- 30% Win Chance Logic ---
        if random.randint(1, 100) <= 30: 
            draw = sorted(random.sample(range(1, 81), 20))
        else:
            pool = list(set(range(1, 81)) - set(users[uid]['selected_num']))
            draw = sorted(random.sample(pool, 20))

        matches = set(users[uid]['selected_num']).intersection(set(draw))
        match_count = len(matches)
        
        # --- ኬኖ ፎርሙላ ---
        multiplier = 10 
        if match_count > 0:
            prize = int((bet_amt * multiplier * match_count) / selected_count)
        else:
            prize = 0
            
        users[uid]['balance'] += prize
        
        result = (f"🎰 **የዕጣ ውጤት**\n\n✅ የወጡት፦ `{draw}`\n"
                  f"🎯 የገጠሙ፦ {match_count}\n"
                  f"💰 ሽልማት፦ {prize} ብር\n"
                  f"💵 ቀሪ ሂሳብ፦ {users[uid]['balance']} ብር")
        
        users[uid]['selected_num'] = [] 
        
        kb = [[InlineKeyboardButton("🎮 Play Again", callback_data="play")],
              [InlineKeyboardButton("🏠 Main Menu", callback_data="menu")]]
        await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
        return

    # Withdraw እና ሌሎች ተግባራት እንዳሉ ናቸው...
    if data == "withdraw":
        context.user_data["state"] = "AWAITING_WITHDRAW_AMT"
        await query.edit_message_text("💸 ማውጣት የሚፈልጉትን መጠን ይጻፉ፦", reply_markup=back_kb())
        return

    if data == "balance":
        await query.edit_message_text(f"🏦 ያሎት ቀሪ ሂሳብ፦ {users[uid]['balance']} ብር", reply_markup=main_menu_keyboard())
        return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    ensure_user(uid)
    state = context.user_data.get("state")

    if state == "AWAITING_BET" and text.isdigit():
        bet = int(text)
        if bet < 10:
            await update.message.reply_text("❌ ዝቅተኛ ውርርድ 10 ብር ነው።", reply_markup=back_kb())
            return
        if bet > users[uid]['balance']:
            await update.message.reply_text(f"❌ በቂ ሂሳብ የለዎትም (ያሎት፦ {users[uid]['balance']} ብር)።", reply_markup=back_kb())
            return
        users[uid]["bet"] = bet
        context.user_data["state"] = None
        await update_game_ui(update, uid)

    # (የቀሩት Handlers እንዳሉ ናቸው...)
