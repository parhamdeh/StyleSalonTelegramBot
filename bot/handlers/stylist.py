import sys
import os




path = os.path.join(os.path.dirname(__file__), '..', 'db')
sys.path.append(path)
path1 = os.path.join(os.path.dirname(__file__), '..', 'bot')
sys.path.append(path1)
import jdatetime
import mongo

from telethon import events, Button
from datetime import datetime, timezone
from telethon.tl.custom.button import Button


async def handle_callback(event, data, bot):
    if data == "use_product":
        await use_product(event, bot)
    elif data == "stylist_report":
        await stylist_report(event, bot)
    elif data == "list_products":
        await list_products(event)
    await event.answer()

async def use_product(event, bot):
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
            buttons.append([Button.text("اتمام آرایش")])

            if not buttons:
                await conv.send_message("محصولی برای نمایش موجود نیست.")
                break

            buttons = flatten_buttons(buttons)
            await conv.send_message("محصولی که استفاده کردی را انتخاب کن:", buttons=buttons)

            response = await conv.get_response()
            text = response.text.strip()

            if text == "صفحه بعد":
                page += 1
                continue
            elif text == "صفحه قبل":
                page -= 1
                continue
            elif text == "اتمام آرایش":
                break

            product_name = text
            product = mongo.mongo_manager.get_product(product_name)
            if not product:
                await conv.send_message("محصول پیدا نشد.")
                continue

            await conv.send_message("چند گرم استفاده کردی؟")
            try:
                amount = float((await conv.get_response()).text.strip())
            except:
                await conv.send_message("مقدار نامعتبر است. لطفاً یک عدد وارد کن.")
                continue

            # کاهش موجودی در دیتابیس
            return_method = mongo.mongo_manager.reduce_product_stock(product_name, amount)
            await event.reply(return_method)
            current_stock = product["total_weight"]
        
            if current_stock <=0: 
                products = mongo.mongo_manager.get_products()
                for pro in products:
                    if pro["name"] == product_name:
                        if pro["total_weight"] > 0:
                            unit_price = pro["price_per_gram"]
                            total_price = unit_price * amount
                            items.append({
                                "product_name": product["name"],
                                "unit_price": unit_price,
                                "total_price": total_price
                            })
            else:
                unit_price = float(product["price_per_gram"])
                total_price = unit_price * amount
                items.append({
                    "product_name": product["name"],
                    "unit_price": unit_price,
                    "total_price": total_price
                })

        # اطلاعات نهایی
        await conv.send_message("نام مشتری:")
        customer_name = (await conv.get_response()).text.strip()

        await conv.send_message("پرداخت نهایی مشتری:")
        try:
            customer_price = float((await conv.get_response()).text.strip())
        except:
            await conv.send_message("مبلغ نامعتبر وارد شده. عملیات لغو شد.")
            return

        sender = await event.get_sender()
        sender_id = sender.id
        print(sender_id)
        user = mongo.mongo_manager.get_user_by_telegram2(sender_id)
        invoice = mongo.mongo_manager.create_invoice(
            stylist_id=user["name"],
            customer_name=customer_name,
            customer_price=customer_price,
            items=items
        )

        await conv.send_message(f"✅ ثبت شد. کل مبلغ: {customer_price}")

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

async def stylist_report(event, bot):
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
    
    stylist = mongo.mongo_manager.get_user_by_telegram(event.sender_id)
    report = mongo.mongo_manager.get_stylist_report(stylist["name"], from_date, to_date)
    if not report:
        await event.respond(" گزارشی برای شما یافت نشد.")
        return

    await event.respond(
        f" گزارش شما:\n"
        f"کل درآمد: {report['total']}\n"
        f"سهم شما: {report['stylist_profit']}"
    )

async def list_products(event):
    products = mongo.mongo_manager.list_products()
    if not products:
        await event.respond(" محصولی ثبت نشده.")
        return

    text = " محصولات:\n"
    for p in products:
        text += f"- {p['name']} | موجودی: {p['total_weight']} {p['unit']}\n"
    await event.respond(text)

def navigate(msg, current_page=1, total_pages=1, data=None, delimiter='-'):
    current_page = int(current_page)
    total_pages = int(total_pages)
    if data:
        data += delimiter
        keyboard = []
        if total_pages > current_page + 1:
            keyboard.append(Button.inline('last', str.encode(data + str(total_pages))))
        if total_pages > current_page:
            keyboard.append(Button.inline('next', str.encode(data + str(current_page + 1))))
        if total_pages > 1:
            keyboard.append(Button.inline(str(current_page) + ' from ' + str(total_pages)))
        if current_page > 1:
            keyboard.append(Button.inline('previous', str.encode(data + str(current_page - 1))))
        if current_page > 2:
            keyboard.append(Button.inline('first', str.encode(data + '1')))
        return keyboard
    else:
        return None

def paginate(msg, current_page=1, total_pages=1, data=None, delimiter='-',
             before=None, after=None):
    if data:
        paginator = navigate(msg, current_page, total_pages, data, delimiter)
        if before or after:
            paginator = [paginator]
        if before:
            paginator = before + paginator
        if after:
            paginator.append(after)
        return paginator
    else:
        return None