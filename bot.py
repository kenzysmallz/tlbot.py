import os
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("BOT_TOKEN")
user_data = {}

def get_btc_price():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd",
            timeout=8
        )
        return float(r.json()["bitcoin"]["usd"])
    except Exception:
        return 30000.0

def get_sidebar():
    keyboard = [
        [InlineKeyboardButton("⛏ Mine", callback_data="mine")],
        [InlineKeyboardButton("📊 Balance", callback_data="balance")],
        [InlineKeyboardButton("📤 Withdraw", callback_data="withdraw")],
        [InlineKeyboardButton("➕ Add Wallet", callback_data="add_wallet")],
        [InlineKeyboardButton("ℹ️ About Info", callback_data="about")],
        [InlineKeyboardButton("👥 Referral", callback_data="referral")]
    ]
    return InlineKeyboardMarkup(keyboard)

def ensure_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"balance": 0.0, "wallet": None, "last_check": time.time(), "referral_bonus": 0.0}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ensure_user(user_id)
    if context.args:
        referrer_id = context.args[0]
        if referrer_id != str(user_id):
            ensure_user(referrer_id)
            user_data[referrer_id]["balance"] += 0.10 / get_btc_price()

    await update.message.reply_text(
        "👋 Welcome to Telegram Bit Miner! 🚀\n"
        "⏳ Earnings: $0.50 every 2 minutes continuously.\n"
        "Tap buttons below to start:",
        reply_markup=get_sidebar()
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    ensure_user(user_id)
    data = user_data[user_id]
    now = time.time()
    elapsed = now - data["last_check"]
    btc_per_2min = 0.5 / get_btc_price()
    btc_per_sec = btc_per_2min / 120
    data["balance"] += btc_per_sec * elapsed
    data["last_check"] = now
    usd_balance = data["balance"] * get_btc_price()

    if query.data == "mine":
        await query.edit_message_text("⛏ Mining runs automatically.\n💰 Earn $0.50 every 2 minutes.", reply_markup=get_sidebar())
    elif query.data == "balance":
        progress_fraction = (elapsed % 120) / 120
        progress_steps = int(progress_fraction * 10)
        bar = "🔺" * progress_steps + "▫️" * (10 - progress_steps)
        seconds_remaining = max(0, int(120 - (elapsed % 120)))
        await query.edit_message_text(
            f"📊 Balance:\n{bar}\n💰 {data['balance']:.6f} BTC (~${usd_balance:.2f})\n⏱ Next credit in: {seconds_remaining} sec",
            reply_markup=get_sidebar()
        )
    elif query.data == "add_wallet":
        await query.edit_message_text("💳 Please send your BTC wallet address.", reply_markup=get_sidebar())

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ensure_user(user_id)
    text = update.message.text.strip()
    if text.startswith(("1", "3", "bc1")):
        user_data[user_id]["wallet"] = text
        await update.message.reply_text(f"✅ BTC wallet saved: {text}", reply_markup=get_sidebar())
    else:
        await update.message.reply_text("⚠️ Invalid input. Tap buttons below.", reply_markup=get_sidebar())

def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    # Just run polling — handles initialize/start automatically
    app.run_polling()

if __name__ == "__main__":
    main()
