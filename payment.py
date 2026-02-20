from datetime import date
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# ================= SYSTEM =================
class System:
    def __init__(self):
        self._users = []
        self._booking = []
        self._promotions = []

    def add_user(self, user):
        self._users.append(user)

    def add_booking(self, booking):
        self._booking.append(booking)

    def add_promotion(self, promo):
        self._promotions.append(promo)

SYSTEM = System()

# ================= USER =================
class User:
    def __init__(self, user_id, membership_level):
        self._user_id = user_id
        self._membership_level = membership_level
        self._coupons = []

    def add_coupon(self, coupon):
        self._coupons.append(coupon)

    def calculate_membership(self):
        if self._membership_level == "gold":
            return 0.20
        elif self._membership_level == "silver":
            return 0.10
        return 0.0

    def get_coupon_list(self):
        return self._coupons

# ================= COUPON =================
class Coupon:
    def __init__(self, code, discount, expiry_date):
        self._code = code
        self._discount = discount
        self._expiry_date = expiry_date
        self._is_used = False

    def validate_coupon(self, code):
        if self._code == code and not self._is_used and date.today() <= self._expiry_date:
            return self._discount
        return 0.0

    def use(self):
        self._is_used = True

# ================= PROMOTION =================
class Promotion:
    def __init__(self, promo_id, discount_rate, min_price, expiry_date):
        self._promo_id = promo_id
        self._discount_rate = discount_rate
        self._min_price = min_price
        self._expiry_date = expiry_date

    def get_valid_promotion(self, base_price):
        if base_price >= self._min_price and date.today() <= self._expiry_date:
            return base_price * self._discount_rate
        return 0.0

# ================= BOOKING =================
class Booking:
    def __init__(self, booking_id, user):
        self._booking_id = booking_id
        self._user = user
        self._items = []
        self._base_price = 0
        self._status = "pending"

    def add_item(self, item):
        self._items.append(item)
        self._base_price += item.price

    def get_booking_item(self):
        return self._items, self._base_price

    def confirm(self):
        self._status = "confirmed"

# ================= PAYMENT =================
class Payment:
    def calculate_price(self, base, promo, member_rate, coupon):
        total = base - promo
        total -= total * member_rate
        total -= coupon
        return max(total, 0)

    def generate_receipt(self, items, amount):
        return {
            "items":[{"type":i.__class__.__name__,"id":i.get_id(),"price":i.price} for i in items],
            "amount":round(amount,2)
        }

# ================= BANK / STAFF =================
class Bank:
    def verify_transfer(self, slip):
        return slip.startswith("OK")

class Staff:
    def verify_cash(self, amount, expected):
        return amount >= expected

# ================= ITEM TYPES =================
class ResidenceBooking:
    def __init__(self, residence_id, price):
        self.residence_id = residence_id
        self.price = price
    def get_id(self):
        return self.residence_id

class ActivityBooking:
    def __init__(self, activity_id, price):
        self.activity_id = activity_id
        self.price = price
    def get_id(self):
        return self.activity_id

# ================= MOCK DATA =================
user1 = User("U001","gold")
user1.add_coupon(Coupon("DISC10",100,date(2026,12,31)))
SYSTEM.add_user(user1)

SYSTEM.add_promotion(Promotion("P1",0.1,1000,date(2026,12,31)))

booking1 = Booking("B001",user1)
booking1.add_item(ResidenceBooking("H1",2000))
booking1.add_item(ActivityBooking("A1",1000))
SYSTEM.add_booking(booking1)

# ================= API MODELS =================
class CalculateRequest(BaseModel):
    booking_id:str
    coupon:str|None=None

class PayRequest(BaseModel):
    booking_id:str
    method:str
    slip:str|None=None
    cash:float|None=None
    coupon:str|None=None

# ================= SUMMARY =================
@app.get("/payment/summary/{booking_id}")
def summary(booking_id:str):
    booking = next((b for b in SYSTEM._booking if b._booking_id==booking_id),None)
    if not booking:
        raise HTTPException(404,"Booking not found")

    items,base = booking.get_booking_item()
    user = booking._user

    promo=max([p.get_valid_promotion(base) for p in SYSTEM._promotions],default=0)
    member=user.calculate_membership()

    return {
        "items":[{"type":i.__class__.__name__,"id":i.get_id(),"price":i.price} for i in items],
        "base_price":base,
        "promotion_discount":promo,
        "membership_discount":member,
        "available_coupons":[c._code for c in user.get_coupon_list()]
    }

# ================= CALCULATE PRICE =================
@app.post("/payment/calculate")
def calculate(data:CalculateRequest):
    booking = next((b for b in SYSTEM._booking if b._booking_id==data.booking_id),None)
    if not booking:
        raise HTTPException(404,"Booking not found")

    items,base=booking.get_booking_item()
    user=booking._user

    promo=max([p.get_valid_promotion(base) for p in SYSTEM._promotions],default=0)
    member=user.calculate_membership()

    coupon_discount=0
    if data.coupon:
        for c in user.get_coupon_list():
            coupon_discount=c.validate_coupon(data.coupon)
            if coupon_discount>0: break

    final=Payment().calculate_price(base,promo,member,coupon_discount)

    return {"final_price":final}

# ================= PAY =================
@app.post("/payment/pay")
def pay(data:PayRequest):
    booking = next((b for b in SYSTEM._booking if b._booking_id==data.booking_id),None)
    if not booking:
        raise HTTPException(404,"Booking not found")

    items,base=booking.get_booking_item()
    user=booking._user

    promo=max([p.get_valid_promotion(base) for p in SYSTEM._promotions],default=0)
    member=user.calculate_membership()

    coupon_discount=0
    if data.coupon:
        for c in user.get_coupon_list():
            d=c.validate_coupon(data.coupon)
            if d>0:
                coupon_discount=d
                c.use()
                break

    payment=Payment()
    final=payment.calculate_price(base,promo,member,coupon_discount)

    if data.method=="transfer":
        if not data.slip or not Bank().verify_transfer(data.slip):
            raise HTTPException(400,"Invalid slip")

    elif data.method=="cash":
        if data.cash is None or not Staff().verify_cash(data.cash,final):
            raise HTTPException(400,"Not enough cash")
    else:
        raise HTTPException(400,"Invalid method")

    booking.confirm()
    return {"status":"success","receipt":payment.generate_receipt(items,final)}
