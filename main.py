import requests
from bs4 import BeautifulSoup
import time
import os
import json
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

TOKEN = os.environ.get("TOKEN")
CHECK_INTERVAL = 1800  # كل 30 دقيقة
DATA_FILE = "/data/products.json"

def load_products():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_products(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

def get_product_info(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers)
    soup = BeautifulSoup(r.text, "html.parser")

    title = soup.find("span", {"id": "productTitle"})
    price = soup.find("span", {"class": "a-price-whole"})
    discount = soup.find("span", {"class": "savingsPercentage"})

    title_text = title.text.strip() if title else "منتج"
    price_value = int(price.text.replace(",", "").strip()) if price else None
    discount_text = discount.text.strip() if discount else "0%"

    return title_text, price_value, discount_text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 الأوامر:\n"
        "/add لينك السعر_المستهدف\n"
        "/remove لينك\n"
        "/list"
    )

async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 2:
        await update.message.reply_text("❌ الصيغة: /add لينك السعر")
        return

    url = context.args[0]
    target_price = int(context.args[1])
    chat_id = str(update.effective_chat.id)

    data = load_products()
    if chat_id not in data:
        data[chat_id] = {}

    title, current_price, discount = get_product_info(url)

    if current_price:
        data[chat_id][url] = {
            "title": title,
            "last_price": current_price,
            "target_price": target_price
        }
        save_products(data)
        await update.message.reply_text(
            f"✅ تمت الإضافة\n"
            f"{title}\n"
            f"السعر الحالي: {current_price} جنيه\n"
            f"التنبيه عند: {target_price}"
        )
    else:
        await update.message.reply_text("❌ مش قادر أجيب السعر")

async def remove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return

    url = context.args[0]
    chat_id = str(update.effective_chat.id)

    data = load_products()
    if chat_id in data and url in data[chat_id]:
        del data[chat_id][url]
        save_products(data)
        await update.message.reply_text("🗑 تم الحذف")
    else:
        await update.message.reply_text("❌ اللينك مش موجود")

async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    data = load_products()

    if chat_id not in data or not data[chat_id]:
        await update.message.reply_text("📭 مفيش منتجات")
        return

    text = "📦 منتجاتك:\n\n"
    for url, info in data[chat_id].items():
        text += (
            f"{info['title']}\n"
            f"آخر سعر: {info['last_price']} جنيه\n"
            f"تنبيه عند: {info['target_price']}\n\n"
        )

    await update.message.reply_text(text)

async def check_prices(app):
    while True:
        data = load_products()
        for chat_id, products in data.items():
            for url, info in products.items():
                title, new_price, discount = get_product_info(url)
                if new_price:
                    if new_price <= info["target_price"]:
                        await app.bot.send_message(
                            chat_id=int(chat_id),
                            text=(
                                f"🔥 السعر وصل للهدف!\n"
                                f"{title}\n"
                                f"السعر: {new_price} جنيه\n"
                                f"الخصم: {discount}"
                            )
                        )
                        data[chat_id][url]["last_price"] = new_price
        save_products(data)
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add))
    app.add_handler(CommandHandler("remove", remove))
    app.add_handler(CommandHandler("list", list_products))

    app.job_queue.run_once(lambda ctx: check_prices(app), 0)

    app.run_polling()
