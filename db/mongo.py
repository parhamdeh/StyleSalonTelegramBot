from pymongo import MongoClient, ReturnDocument
import sys
import os

# اضافه کردن مسیر فولدر config به sys.path
config_path = os.path.join(os.path.dirname(__file__), '..', 'config')
sys.path.append(config_path)
from bson import ObjectId
from datetime import datetime, timezone
import settings

class MongoManager:
    def __init__(self):
        self.client = MongoClient(settings.MONGO_URI)
        self.db = self.client[settings.DB_NAME]
        

        self.users = self.db.users
        self.products = self.db.products
        self.invoices = self.db.invoices
        self.withdrawals = self.db.withdrawals


    #  کاربران
    def add_user(self,id ,name, mobile, role="stylist"):
        user = self.users.find_one({"name" : name})
        if user:
            return False
        user = {
            "id" : id,
            "name": name,
            "mobile": mobile,
            "role": role,
            "balance": 0,
            "telegram_id": None,
        }
        return self.users.insert_one(user).inserted_id

    def update_user_telegram_id(self, user_id, telegram_id):
        return self.users.find_one_and_update(
            {"id": user_id},
            {"$set": {"telegram_id": telegram_id}},
            return_document=ReturnDocument.AFTER,
        )

    def get_user_by_telegram(self, telegram_id):
        return self.users.find_one({"telegram_id": telegram_id})
    def get_user_by_telegram2(self, telegram_id):
        return self.users.find_one({"id": telegram_id})
    
    def get_user_by_telegram3(self, telegram_id):
        return self.users.find_one({"id": telegram_id})

    def get_user_by_mobile(self, mobile):
        return self.users.find_one({"mobile": mobile})

    #  محصولات
    def add_product(self, name, unit, total_weight, price_per_gram):
        product = {
            "name": name,
            "unit": unit,
            "total_weight": total_weight,
            "price_per_gram": price_per_gram,
            "created_at": datetime.now(timezone.utc),
        }
        return self.products.insert_one(product).inserted_id

    def update_product_stock(self, product_id, amount_used):
        return self.products.find_one_and_update(
            {"id": product_id},
            {"$inc": {"total_weight": -amount_used}},
            return_document=ReturnDocument.AFTER,
        )

    def get_product(self, product_id):
        return self.products.find_one({"name": product_id})
    def get_products(self):
        return self.products.find()

    def list_products(self):
        return list(self.products.find())
    
    def count_products(self):
        return self.products.count_documents({})
    
    def count_stylists(self):
        return self.users.count_documents({})
    
    def list_products2(self):
        return self.products.find()
    # 📋 فاکتور
    def create_invoice(self, stylist_id, customer_name, customer_price, items):
        """
        items: list of dicts
        [
            {"product_id": <ObjectId>, "amount": 20, "unit_price": 2.5, "total_price": 50},
            ...
        ]
        """
        total = sum(item["total_price"] for item in items)
        end_pro = customer_price - total
        stylist_profit = end_pro * 0.4
        owner_profit = end_pro * 0.6
        for dic in items:
            item_lst = list(dic.keys())

        invoice = {
            "id": stylist_id,
            "customer_name": customer_name,
            "customer_price" : customer_price,
            "date": datetime.now(timezone.utc),
            "items": item_lst,
            "total": customer_price,
            "profit_split": {
                "stylist": stylist_profit,
                "owner": owner_profit,
            },
        }

        self.invoices.insert_one(invoice)

        # افزایش موجودی آرایشگر
        self.users.update_one(
            {"name": stylist_id},
            {"$inc": {"balance": stylist_profit}}
        )

        return invoice
    # 📋 تسویه
    def withdraw(self, stylist_id, note=""):
        user = self.users.find_one({"name": stylist_id})
        
        amount = user.get("balance", 0)
        if amount <= 0:
            return f"موجودی حساب صفر تومان است."

        withdrawal = {
            "stylist_id": stylist_id,
            "amount": amount,
            "date": datetime.now(timezone.utc),
            "note": note,
        }

        self.withdrawals.insert_one(withdrawal)
        

        # صفر کردن موجودی
        self.users.update_one(
            {"name": stylist_id},
            {"$set": {"balance": 0}}
        )

        return f"تسویه {amount} تومان با آرایشگر {stylist_id} انجام شد"
# ##
    def get_profit_report(self, from_date, to_date):
        """
        گزارش سود کلی سالن بین دو تاریخ
        """
        print(from_date)
        print(to_date)
        pipeline = [
            {
                "$match": {
                    "date": {
                        "$gte": from_date,
                        "$lte": to_date
                    }
                }
            },
            {
                "$group": {
                    "_id": None,  # گروه‌بندی کلی (یک سطر نتیجه)
                    "total": {"$sum": "$total"},
                    "total_owner": {"$sum": "$profit_split.owner"},
                    "total_stylist": {"$sum": "$profit_split.stylist"}
                }
            }
        ]
        result = list(self.invoices.aggregate(pipeline))
        if result:
            return result[0]
        return {
            "total": 0,
            "total_owner": 0,
            "total_stylist": 0
        }

    def get_stylist_report(self, stylist_id, from_date, to_date):
        """
        گزارش درآمد آرایشگر بین دو تاریخ
        """
        print(from_date)
        print(to_date)

        pipeline = [
            {
                "$match": {
                    "id": stylist_id,  # فیلتر بر اساس نام آرایشگر
                    "date": {
                        "$gte": from_date,
                        "$lte": to_date
                    }
                }
            },
            {
                "$group": {
                    "_id": "$stylist_name",  # گروه‌بندی بر اساس نام آرایشگر
                    "total": {"$sum": "$total"},
                    "stylist_profit": {"$sum": "$profit_split.stylist"}
                }
            }
        ]
        result = list(self.invoices.aggregate(pipeline))
        if result:
            return result[0]
        return {
            "total": 0,
            "stylist_profit": 0
        }

    def delete_stylist(self, name):
        """
        حذف یک آرایشگر بر اساس نام
        """
        result = self.users.delete_many({
            "name": name,
            "role": "stylist"
        })
        if result.deleted_count > 0:
            print(f"{result.deleted_count} آرایشگر با نام {name} حذف شد.")
        
    def delete_product(self, name):
            """
            حذف محصول(ها) بر اساس نام.
            اگر چند محصول با این نام باشند، همه حذف می‌شوند.
            """
            products = list(self.products.find({"name": name}))
            
            if not products:
                return {
                    "success": False,
                    "message": f" محصولی با نام «{name}» پیدا نشد.",
                    "count": 0
                }

            result = self.products.delete_many({"name": name})
            return {
                "success": True,
                "message": f"✅ محصول با نام «{name}» حذف شد.",
                "count": result.deleted_count
            }
    
    def reduce_product_stock(self, product_id, amount):
        """
        کم کردن موجودی محصول (مصرف توسط آرایشگر).
        اگر موجودی کافی نباشد، مقدار جدید ۰ می‌شود و پیام می‌دهد که تمام شده.
        """
        product = self.get_product(product_id)

        current_stock = product["total_weight"]
        print(current_stock)
        if current_stock <=0 :
            
            products = self.get_products()
            for pro in products:
                if pro["name"] == product_id:
                    if pro["total_weight"] > 0:
                        real = pro["price_per_gram"]
                        print(real)
                        new_stock = pro["total_weight"] - amount
                        if new_stock <= 0:
                            # موجودی تموم شد
                            self.products.update_one(
                                {"name": pro["name"], "price_per_gram" : real},
                                {"$set": {"total_weight": 0}}
                                )
                            return (f"⚠️ محصول «{product['name']}» تمام شد!")

                        self.products.update_one(
                        {"name": product["name"], "price_per_gram" : real},
                        {"$set": {"total_weight": new_stock}}
                         )
                        return f"✅ {amount} از «{product['name']}» کم شد. موجودی جدید: {new_stock}"
            
        new_stock = current_stock - amount

        if new_stock <= 0:
            # موجودی تموم شد
            self.products.update_one(
                {"name": product["name"]},
                {"$set": {"total_weight": 0}}
                )
            return (f"⚠️ محصول «{product['name']}» تمام شد!")
            
        # موجودی هنوز مثبت است
        self.products.update_one(
            {"name": product["name"]},
            {"$set": {"total_weight": new_stock}}
        )
        return f"✅ {amount} از «{product['name']}» کم شد. موجودی جدید: {new_stock}"
    
    def increase_product_stock(self, product_id, amount):
        """
        اضافه کردن موجودی محصول (خرید توسط مدیر).
        """
        product = self.get_product(product_id)
        

        new_stock = round(product["total_weight"] + amount, 2)

        self.products.update_one(
            {"name": product["name"]},
            {"$set": {"total_weight": new_stock}}
        )
        return f"✅ {amount} به موجودی «{product['name']}» اضافه شد. موجودی جدید: {new_stock}"
    
    def update_product_price(self, product_id, new_price):
        """
        تغییر قیمت هر واحد محصول (توسط مدیر).
        """
        product = self.get_product(product_id)
        if not product:
            return " !محصول پیدا نشد."

        self.products.update_one(
            {"name": product["name"]},
            {"$set": {"price_per_gram": new_price}}
        )

        return f"✅ قیمت محصول «{product['name']}» به {new_price} به‌روزرسانی شد."

    def see_invoice(self):
        return self.invoices.find()


mongo_manager = MongoManager()