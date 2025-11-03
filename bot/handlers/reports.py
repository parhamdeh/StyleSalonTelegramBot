import os
import sys

path = os.path.join(os.path.dirname(__file__), '..', 'db')
sys.path.append(path)

import mongo
from datetime import datetime, timezone


async def report_profit(event, from_date=None, to_date=None):
    """
    گزارش سود کلی (برای مدیر)
    """
    from_date = from_date or datetime(1970, 1, 1)
    to_date = to_date or datetime.now(timezone.utc)

    report = mongo.MongoManager.get_profit_report(from_date, to_date)
    if not report:
        await event.respond(" هیچ درآمدی در این بازه ثبت نشده.")
        return

    await event.respond(
        f" گزارش سود:\n"
        f"کل: {report['total']}\n"
        f"سهم سالن: {report['total_owner']}\n"
        f"سهم آرایشگرها: {report['total_stylist']}"
    )


async def stylist_report(event, stylist_id, from_date=None, to_date=None):
    """
    گزارش سود شخصی آرایشگر
    """
    from_date = from_date or datetime(1970, 1, 1)
    to_date = to_date or datetime.now(timezone.utc)

    report = mongo.MongoManager.get_stylist_report(stylist_id, from_date, to_date)
    if not report:
        await event.respond(" گزارشی برای شما یافت نشد.")
        return

    await event.respond(
        f" گزارش شما:\n"
        f"کل درآمد: {report['total']}\n"
        f"سهم شما: {report['stylist_profit']}"
    )