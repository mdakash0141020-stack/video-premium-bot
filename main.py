import os
import sqlite3
from datetime import datetime, timedelta, timezone

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0") or 0)
BKASH_NUMBER = os.getenv("BKASH_NUMBER", "01609230133").strip()
MONTHLY_PRICE = 300
DB = "bot_data.sqlite3"

def db():
    con = sqlite3.connect(DB)
    con.execute("""CREATE TABLE IF NOT EXISTS users
        (user_id INTEGER PRIMARY KEY, expires_at TEXT)""")
    con.execute("""CREATE TABLE IF NOT EXISTS payments
        (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
         trx TEXT, status TEXT DEFAULT 'pending')""")
    con.execute("""CREATE TABLE IF NOT EXISTS videos
        (id INTEGER PRIMARY KEY AUTOINCREMENT, file_id TEXT, caption TEXT)""")
    con.commit()
    return con

def is_admin(user_id):
    return ADMIN_ID and user_id == ADMIN_ID

def premium_active(user_id):
    con = db()
    row = con.execute("SELECT expires_at FROM users WHERE user_id=?", (user_id,)).fetchone()
    con.close()
    if not row:
        return False
    try:
        return datetime.fromisoformat(row[0]) > datetime.now(timezone.utc)
    except Exception:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("আমি ১৮ বছর বা তার বেশি বয়সী", callback_data="age_yes")]]
    await update.message.reply_text(
        "এই বটটি শুধুমাত্র ১৮ বছর বা তার বেশি বয়সীদের জন্য। "
        "শুধু আইনসম্মত, সম্মতিপূর্ণ এবং নিজের/অনুমতিপ্রাপ্ত ভিডিও ব্যবহার করা হবে। "
        "আপনি কি ১৮+?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "age_yes":
        context.user_data["age_ok"] = True
        await q.message.reply_text(
            f"প্রিমিয়াম মূল্য: ৩০০ টাকা / ৩০ দিন।\n"
            f"বিকাশ Send Money: {BKASH_NUMBER}\n\n"
            "পেমেন্ট করার পর /submit লিখে Transaction ID পাঠান। "
            "অ্যাডমিন টাকা যাচাই করে অনুমোদন করবেন।"
        )
    elif q.data.startswith("approve:") or q.data.startswith("reject:"):
        if not is_admin(q.from_user.id):
            await q.edit_message_text("অনুমতি নেই।")
            return
        action, payment_id = q.data.split(":")
        con = db()
        row = con.execute("SELECT user_id FROM payments WHERE id=? AND status='pending'",
                          (int(payment_id),)).fetchone()
        if not row:
            con.close()
            await q.edit_message_text("এই পেমেন্টটি আর pending নেই।")
            return
        user_id = row[0]
        if action == "approve":
            expires = datetime.now(timezone.utc) + timedelta(days=30)
            con.execute("INSERT INTO users(user_id, expires_at) VALUES(?, ?) "
                        "ON CONFLICT(user_id) DO UPDATE SET expires_at=excluded.expires_at",
                        (user_id, expires.isoformat()))
            con.execute("UPDATE payments SET status='approved' WHERE id=?", (int(payment_id),))
            await context.bot.send_message(user_id, "আপনার পেমেন্ট অনুমোদিত হয়েছে। ৩০ দিনের প্রিমিয়াম চালু হয়েছে। /videos লিখুন।")
            await q.edit_message_text(f"পেমেন্ট অনুমোদিত। User ID: {user_id}")
        else:
            con.execute("UPDATE payments SET status='rejected' WHERE id=?", (int(payment_id),))
            await context.bot.send_message(user_id, "পেমেন্ট যাচাই করা যায়নি। অনুগ্রহ করে অ্যাডমিনের সঙ্গে যোগাযোগ করুন।")
            await q.edit_message_text(f"পেমেন্ট বাতিল। User ID: {user_id}")
        con.commit()
        con.close()

async def submit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("age_ok"):
        await update.message.reply_text("আগে /start দিয়ে ১৮+ নিশ্চিত করুন।")
        return
    context.user_data["waiting_trx"] = True
    await update.message.reply_text(
        f"{BKASH_NUMBER} নম্বরে ৩০০ টাকা Send Money করার পর আপনার Transaction ID পাঠান।"
    )

async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.pop("waiting_trx", False):
        trx = (update.message.text or "").strip()
        if len(trx) < 5:
            await update.message.reply_text("সঠিক Transaction ID দিন।")
            return
        con = db()
        cur = con.execute("INSERT INTO payments(user_id, trx) VALUES(?, ?)",
                          (update.effective_user.id, trx))
        payment_id = cur.lastrowid
        con.commit()
        con.close()
        await update.message.reply_text("Transaction ID অ্যাডমিনের কাছে পাঠানো হয়েছে। যাচাই শেষে জানানো হবে।")
        if ADMIN_ID:
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("Approve", callback_data=f"approve:{payment_id}"),
                InlineKeyboardButton("Reject", callback_data=f"reject:{payment_id}")
            ]])
            await context.bot.send_message(
                ADMIN_ID,
                f"নতুন পেমেন্ট\nUser ID: {update.effective_user.id}\n"
                f"Transaction ID: {trx}\nAmount: 300 BDT",
                reply_markup=keyboard,
            )
        return
    await update.message.reply_text("কমান্ড: /start, /submit, /videos")

async def videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("age_ok"):
        await update.message.reply_text("আগে /start দিয়ে ১৮+ নিশ্চিত করুন।")
        return
    if not premium_active(update.effective_user.id):
        await update.message.reply_text("প্রিমিয়াম চালু নেই। /submit দিয়ে পেমেন্ট করুন।")
        return
    con = db()
    rows = con.execute("SELECT file_id, caption FROM videos ORDER BY id DESC").fetchall()
    con.close()
    if not rows:
        await update.message.reply_text("এখনও কোনো ভিডিও যোগ করা হয়নি।")
        return
    for file_id, caption in rows:
        await context.bot.send_video(update.effective_chat.id, file_id, caption=caption or None)

async def addvideo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("শুধু অ্যাডমিন এই কমান্ড ব্যবহার করতে পারবেন।")
        return
    context.user_data["waiting_video"] = True
    await update.message.reply_text("এখন একটি ভিডিও পাঠান। শুধু আইনসম্মত ও সম্মতিপূর্ণ কনটেন্ট যোগ করবেন।")

async def video_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.pop("waiting_video", False):
        return
    if not is_admin(update.effective_user.id):
        return
    video = update.message.video
    if not video:
        await update.message.reply_text("ভিডিও হিসেবে পাঠান, ফাইল/ডকুমেন্ট হিসেবে নয়।")
        return
    caption = update.message.caption or ""
    con = db()
    con.execute("INSERT INTO videos(file_id, caption) VALUES(?, ?)", (video.file_id, caption))
    con.commit()
    con.close()
    await update.message.reply_text("ভিডিও যোগ হয়েছে।")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    con = db()
    row = con.execute("SELECT expires_at FROM users WHERE user_id=?",
                      (update.effective_user.id,)).fetchone()
    con.close()
    if row and premium_active(update.effective_user.id):
        await update.message.reply_text(f"প্রিমিয়াম চালু আছে। মেয়াদ শেষ: {row[0]}")
    else:
        await update.message.reply_text("প্রিমিয়াম চালু নেই।")

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN environment variable is missing")
    if not ADMIN_ID:
        raise RuntimeError("ADMIN_ID environment variable is missing")
    db().close()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("submit", submit))
    app.add_handler(CommandHandler("videos", videos))
    app.add_handler(CommandHandler("addvideo", addvideo))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.VIDEO, video_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    app.run_polling()

if __name__ == "__main__":
    main()
