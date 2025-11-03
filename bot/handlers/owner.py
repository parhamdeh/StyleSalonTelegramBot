import sys
import os

path = os.path.join(os.path.dirname(__file__), '..', 'db')
sys.path.append(path)
import jdatetime
import mongo
from telethon import events, Button
from datetime import datetime, timezone


async def handle_callback(event, data, bot):
    if data == "add_stylist":
        await add_stylist(event, bot)
    elif data == "add_product":
        await add_product(event, bot)
    elif data == "report_profit":
        await report_profit(event, bot)
    elif data == "list_products":
        await list_products(event)
    elif data == "list_stylists":
        await list_stylists(event)
    
    elif data == "delete_stylists":
        await delete_stylists(event, bot)
    elif data == "delete_product":
        await delete_products(event, bot)
    elif data == "update_product_price":
        await update_product_price(event, bot)
    elif data == "withdraw":
        await withdraw(event, bot)
    elif data == "see_invoice":
        await see_invoice(event)
    
    await event.answer()

async def add_stylist(event, bot):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message(" آیدی تلگرام آرایشگر را بدون @ وارد کنید: ")
        telegram_id = (await conv.get_response()).text.strip()

        await conv.send_message(" نام آرایشگر را وارد کنید:")
        name = (await conv.get_response()).text.strip()

        await conv.send_message(" شماره موبایل آرایشگر را وارد کنید:")
        mobile = (await conv.get_response()).text.strip()

        add = mongo.mongo_manager.add_user(telegram_id, name, mobile)
        if add == False:
            await conv.send_message("آرایشگر با این اسم در سیستم وجود دارد.")
            return
        await conv.send_message(f"✅ آرایشگر {name} با شماره {mobile} اضافه شد.")

async def add_product(event, bot):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message(" نام محصول را وارد کنید:")
        name = (await conv.get_response()).text.strip()
        product = mongo.mongo_manager.get_product(name)

        await conv.send_message(" واحد محصول (مثل گرم) را وارد کنید:")
        unit = (await conv.get_response()).text.strip()

        await conv.send_message(" مقدار اولیه محصول را وارد کنید:")
        weight = float((await conv.get_response()).text.strip())

        await conv.send_message(" قیمت هر واحد را وارد کنید:")
        price = float((await conv.get_response()).text.strip())
        if product and product["price_per_gram"] == price:
            now = mongo.mongo_manager.increase_product_stock(name, weight)
            await conv.send_message(now)


        mongo.mongo_manager.add_product(name, unit, weight, price)
        await conv.send_message(f"✅ محصول {name} ثبت شد.")

async def report_profit(event, bot):
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message(" تاریخ اولیه را وارد کنید. مثال 1402/01/01 ")
        from_date_str = (await conv.get_response()).text.strip()

        await conv.send_message(" تاریخ ثانویه را وارد کنید. مثال 1402/01/01 ")
        to_date_str = (await conv.get_response()).text.strip()
        from_date_jalali = jdatetime.datetime.strptime(from_date_str, "%Y/%m/%d")
        to_date_jalali = jdatetime.datetime.strptime(to_date_str, "%Y/%m/%d")
        
        from_date = from_date_jalali.togregorian()
        to_date = to_date_jalali.togregorian().replace(hour=23, minute=59, second=59)
        
        # اطمینان از اینکه تاریخ‌ها در منطقه زمانی UTC هستند
        from_date = from_date.replace(tzinfo=timezone.utc)
        to_date = to_date.replace(tzinfo=timezone.utc)
        
        report = mongo.mongo_manager.get_profit_report(from_date, to_date)
        if not report:
            await event.respond("هیچ درآمدی ثبت نشده.")
            return
        
        await event.respond(
            f"گزارش سود از {from_date_str} تا {to_date_str}:\n"
            f"کل: {report['total']}\n"
            f"سهم سالن: {report['total_owner']}\n"
            f"سهم آرایشگرها: {report['total_stylist']}"
        )
            
async def list_products(event):
    products = mongo.mongo_manager.list_products()
    if not products:
        await event.respond(" محصولی ثبت نشده.")
        return

    text = " محصولات:\n"
    for p in products:
        text += f"- {p['name']} | موجودی: {p['total_weight']} {p['unit']} | قیمت: {p['price_per_gram']} / واحد\n"
    await event.respond(text)

async def list_stylists(event):
    users = mongo.mongo_manager.users.find({"role": "stylist"})
    text = " آرایشگرها:\n"
    for u in users:
        balance = u.get("balance", 0)
        text += f"- {u['name']} |  {u['mobile']} |  موجودی: {balance}\n"
    await event.respond(text)

async def list_stylists2(name):
    users = mongo.mongo_manager.users.find({"role": "stylist"})
    text = " آرایشگر \n"
    for u in users:
        if u['name'] == name:
            balance = u.get("balance", 0)
            text += f"- {u['name']} |  {u['mobile']} |  موجودی: {balance}\n"
            return text

async def delete_stylists(event, bot):
    PRODUCTS_PER_PAGE = 5  
    items = []

    total_products = mongo.mongo_manager.count_stylists()
    total_pages = (total_products + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
    async with bot.conversation(event.sender_id) as conv:
        page = 1
        while True:
            cursor = mongo.mongo_manager.users.find({"role": "stylist"}).skip((page - 1) * PRODUCTS_PER_PAGE).limit(PRODUCTS_PER_PAGE)

            buttons = []
            for user in cursor:
                buttons.append([Button.text(user["name"])])

            # دکمه‌های صفحه‌بندی
            nav_buttons = []
            if total_pages > 1:
                if page > 1:
                    nav_buttons.append(Button.text("صفحه قبل"))
                if page < total_pages:
                    nav_buttons.append(Button.text("صفحه بعد"))

            if nav_buttons:
                buttons.append(nav_buttons)
            buttons.append([Button.text("بازگشت")])

            if not buttons:
                await conv.send_message("آرایشگری برای نمایش موجود نیست")
                break

            buttons = flatten_buttons(buttons)
            await conv.send_message("آرایشگری که میخوای حذف کنی انتخاب کن: ", buttons=buttons)

            response = await conv.get_response()
            text = response.text.strip()

            if text == "صفحه بعد":
                page += 1
                continue
            elif text == "صفحه قبل":
                page -= 1
                continue
            elif text == "بازگشت":
                break

            name = text


            mongo.mongo_manager.delete_stylist(name)
            await event.reply(f"آرایشگر {name} حذف شد")

async def delete_products(event, bot):
    PRODUCTS_PER_PAGE = 5  
    items = []

    total_products = mongo.mongo_manager.count_products()
    total_pages = (total_products + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
    async with bot.conversation(event.sender_id) as conv:
        page = 1
        while True:
            cursor = mongo.mongo_manager.list_products2().skip((page - 1) * PRODUCTS_PER_PAGE).limit(PRODUCTS_PER_PAGE)

            buttons = []
            for product in cursor:
                if int(product["total_weight"]) > 0:
                    buttons.append([Button.text(product["name"])])

            # دکمه‌های صفحه‌بندی
            nav_buttons = []
            if total_pages > 1:
                if page > 1:
                    nav_buttons.append(Button.text("صفحه قبل"))
                if page < total_pages:
                    nav_buttons.append(Button.text("صفحه بعد"))

            if nav_buttons:
                buttons.append(nav_buttons)
            buttons.append([Button.text("بازگشت")])

            if not buttons:
                await conv.send_message("محصولی برای نمایش موجود نیست.")
                break

            buttons = flatten_buttons(buttons)
            await conv.send_message("محصولی که میخوای حذف کنی انتخاب کن: ", buttons=buttons)

            response = await conv.get_response()
            text = response.text.strip()

            if text == "صفحه بعد":
                page += 1
                continue
            elif text == "صفحه قبل":
                page -= 1
                continue
            elif text == "بازگشت":
                break

            name = text
            product = mongo.mongo_manager.get_product(name)
            if not product:
                await conv.send_message("محصول پیدا نشد.")
                continue
            mongo.mongo_manager.delete_product(name)
            await event.reply(f"محصول {name} حذف شد")
     
async def update_product_price(event, bot):
    PRODUCTS_PER_PAGE = 5  
    items = []
    total_products = mongo.mongo_manager.count_products()
    total_pages = (total_products + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
    async with bot.conversation(event.sender_id) as conv:
        page = 1
        while True:
            cursor = mongo.mongo_manager.list_products2().skip((page - 1) * PRODUCTS_PER_PAGE).limit(PRODUCTS_PER_PAGE)

            buttons = []
            for product in cursor:
                if int(product["total_weight"]) > 0:
                    buttons.append([Button.text(product["name"])])

            # دکمه‌های صفحه‌بندی
            nav_buttons = []
            if total_pages > 1:
                if page > 1:
                    nav_buttons.append(Button.text("صفحه قبل"))
                if page < total_pages:
                    nav_buttons.append(Button.text("صفحه بعد"))

            if nav_buttons:
                buttons.append(nav_buttons)
            buttons.append([Button.text("بازگشت")])

            if not buttons:
                await conv.send_message("محصولی برای نمایش موجود نیست.")
                break

            buttons = flatten_buttons(buttons)
            await conv.send_message("محصولی که میخوای قیمتشو تغیر بدی انتخاب کن: ", buttons=buttons)

            response = await conv.get_response()
            text = response.text.strip()

            if text == "صفحه بعد":
                page += 1
                continue
            elif text == "صفحه قبل":
                page -= 1
                continue
            elif text == "بازگشت":
                break

            name = text
            product = mongo.mongo_manager.get_product(name)
            if not product:
                await conv.send_message("محصول پیدا نشد.")
                continue
            await conv.send_message("قیمت جدید هر واحد محصول را وارد کنید: ")
            price = (await conv.get_response()).text.strip()
            now = mongo.mongo_manager.update_product_price(name, price)
            await conv.send_message(now)

async def withdraw(event, bot):
    async with bot.conversation(event.sender_id) as conv:
        
        await conv.send_message(" نام آرایشگر را وارد کنید:")
        name = (await conv.get_response()).text.strip()
        stylists_info = await list_stylists2(name)
        await conv.send_message(stylists_info)    
        now = mongo.mongo_manager.withdraw(name)
        await conv.send_message(now)

def flatten_buttons(buttons):
    flattened = []
    for row in buttons:
        if isinstance(row, list):
            if any(isinstance(el, list) for el in row):
                for subrow in row:
                    if isinstance(subrow, list):
                        flattened.append(subrow)
                    else:
                        flattened.append([subrow])
            else:
                flattened.append(row)
        else:
            flattened.append([row])
    return flattened

def gregorian_to_jalali(gregorian_date):
    return jdatetime.date.fromgregorian(date=gregorian_date)

async def see_invoice(event):
    invoices = mongo.mongo_manager.see_invoice()
    text = "فاکتور ها : \n"
    for invoice in invoices:
        stylist = invoice["id"]
        customer = invoice["customer_name"]
        price = invoice["total"]
        time = invoice["date"]
        jalali_date = gregorian_to_jalali(time)
        text += f"نام آرایشگر : {stylist} \n نام مشتری : {customer} \n مبلغ پرداختی : {price} \n تاریخ : {jalali_date}"
    await event.respond(text)



