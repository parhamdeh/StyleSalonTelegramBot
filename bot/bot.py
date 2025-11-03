import sys
import os

# اضافه کردن مسیر فولدر config به sys.path
config_path = os.path.join(os.path.dirname(__file__), '..', 'config')
sys.path.append(config_path)
path = os.path.join(os.path.dirname(__file__), '..', 'db')
sys.path.append(path)
handlers_path = os.path.join(os.path.dirname(__file__), 'handlers')
sys.path.append(handlers_path)

# حالا می‌توانید ماژول settings را ایمپورت کنید
import settings
from telethon import TelegramClient, events, Button
from telethon.tl.types import PeerUser
import mongo
import owner, stylist

api_id = settings.API_ID
api_hash = settings.API_HASH
bot_token = settings.BOT_TOKEN

bot = TelegramClient('kandipoor', api_id, api_hash).start(bot_token=bot_token)


def is_owner(user_id):
    return user_id == settings.ADMIN_ID


@bot.on(events.NewMessage(pattern='/start', incoming=True))
async def main_handler(event):
    sender = await event.get_sender()
    sender_id = sender.id
    
    user_id = sender.username
    print(sender_id,"sender")
    print(type(sender_id))
    print(user_id,"user")
    

    if is_owner(sender_id):
        buttons = [
                [Button.inline(" آرایشگر جدید", b"add_stylist")],
                [Button.inline(" محصول جدید", b"add_product")],
                [Button.inline(" گزارش سود", b"report_profit")],
                [Button.inline(" موجودی محصولات", b"list_products")],
                [Button.inline(" آرایشگرها", b"list_stylists")],
                [Button.inline("حذف آرایشگر", b"delete_stylists")],
                [Button.inline("حذف محصول", b"delete_product")],
                [Button.inline("تغیر قیمت محصول", b"update_product_price")],
                [Button.inline("تسویه حساب با آرایشگر", b"withdraw")],
                [Button.inline("دیدن فاکتورها", b"see_invoice")],
            ]
        await event.reply("سلام مدیر ! لطفاً یکی از گزینه‌ها را انتخاب کنید:", buttons=buttons)
        
        
        
    else:
        user = mongo.mongo_manager.get_user_by_telegram(sender_id)
        if user:
            buttons = [
                    [Button.inline(" ثبت مصرف مواد", b"use_product")],
                    [Button.inline(" گزارش کارکرد", b"stylist_report")],
                    [Button.inline(" موجودی محصولات", b"list_products")],
                ]
            await event.reply(f"سلام {user['name']} !خوش اومدی", buttons=buttons)
        else:
            user = mongo.mongo_manager.get_user_by_telegram2(user_id)
            if user:
                buttons = [
                        [Button.inline(" ثبت مصرف مواد", b"use_product")],
                        [Button.inline(" گزارش کارکرد", b"stylist_report")],
                        [Button.inline(" موجودی محصولات", b"list_products")],
                    ]
                await event.reply(f"سلام {user['name']} !خوش اومدی", buttons=buttons)
                mongo.mongo_manager.update_user_telegram_id(user_id, sender_id)

            else:
                sender_id2 = str(sender_id)
                user2 = mongo.mongo_manager.get_user_by_telegram2(sender_id2)
                
                if user2:
                    buttons = [
                    [Button.inline(" ثبت مصرف مواد", b"use_product")],
                    [Button.inline(" گزارش کارکرد", b"stylist_report")],
                    [Button.inline(" موجودی محصولات", b"list_products")],
                ]
                    await event.reply(f"سلام {user2['name']} !خوش اومدی", buttons=buttons)
                else:
                    await event.reply("شما در سیستم ثبت نشده‌اید. لطفاً با مدیر تماس بگیرید.")
    return


@bot.on(events.CallbackQuery)
async def callback_handler(event):
    sender_id = event.sender_id
    data = event.data.decode()

    if is_owner(sender_id):
        await owner.handle_callback(event, data, bot)
    else:
        await stylist.handle_callback(event, data, bot)


@bot.on(events.NewMessage(incoming=True, forwards=False, func=lambda e: e.message.media))
async def phone_number(event):
    if type(event.message.peer_id) == PeerUser:
        if event.message.media.phone_number and event.message.media.user_id:
            if event.message.peer_id.user_id == event.message.media.user_id:
                phone_number = event.message.media.phone_number
                if not phone_number.startswith('+'):
                    phone_number = '+' + phone_number
                # Here add stylist user_id to DB and respond with a proper message

if __name__ == "__main__":
    
    bot.run_until_disconnected()
    mongo.MongoManager()
