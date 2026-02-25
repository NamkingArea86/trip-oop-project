from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date

app = FastAPI()

# ---------------- USER ----------------
class User:
    def __init__(self, user_id, level, coupons=None):
        self.user_id = user_id
        self.level = level
        self.coupons = coupons or []

    def membership_rate(self):
        if self.level == "gold":
            return 0.2
        elif self.level == "silver":
            return 0.1
        else:
            return 0


# ---------------- COUPON ----------------
class Coupon:
    def __init__(self, code, discount, expiry):
        self.code = code
        self.discount = discount
        self.expiry = expiry
        self.used = False

    def valid(self):
        return not self.used and date.today() <= self.expiry


# ---------------- PROMOTION ----------------
class Promotion:
    def __init__(self, rate, min_price, expiry):
        self.rate = rate
        self.min_price = min_price
        self.expiry = expiry

    def discount(self, price):
        if price >= self.min_price and date.today() <= self.expiry:
            return price * self.rate
        return 0


# ---------------- RESOURCE TYPES ----------------
class Residencebooking:
    def __init__(self, residence_id, price):
        self.residence_id = residence_id
        self.price = price
        self.status = "pending"

    def reserve(self):
        self.status = "reserved"

    def get_id(self):
        return self.residence_id


class Vehiclebooking:
    def __init__(self, vehicle_id, price):
        self.vehicle_id = vehicle_id
        self.price = price
        self.status = "pending"

    def reserve(self):
        self.status = "reserved"

    def get_id(self):
        return self.vehicle_id


class Activitybooking:
    def __init__(self, activity_id, price):
        self.activity_id = activity_id
        self.price = price
        self.status = "pending"

    def reserve(self):
        self.status = "reserved"

    def get_id(self):
        return self.activity_id


# ---------------- BOOKING ----------------
class Booking:
    def __init__(self, booking_id, user):
        self.booking_id = booking_id
        self.user = user

        # แยกตามที่คุณต้องการ
        self.residence = []
        self.vehicle = []
        self.activity = []

        self.payment_status = "unpaid"

    def get_all_items(self):
        return self.residence + self.vehicle + self.activity

    def base_price(self):
        return sum(i.price for i in self.get_all_items())


# ---------------- PAYMENT ----------------
class Payment:
    @staticmethod
    def calculate(base, promo, member, coupon):
        total = base - promo
        total -= total * member
        total -= coupon
        return max(total, 0)

    @staticmethod
    def receipt(items, amount):
        return {
            "items": [
                {
                    "id": i.get_id(),   
                    "type": i.__class__.__name__,
                    "price": i.price
                } for i in items
            ],
            "amount": round(amount, 2)
        }


# ---------------- BANK ----------------
class Bank:
    @staticmethod
    def verify(slip):
        return slip and slip.startswith("OK")


# ---------------- SYSTEM ----------------
class System:
    def __init__(self):
        self.promotions = []

    # STEP 1 : preview
    def preview(self, user, booking):

        base = booking.base_price()

        promo = max([p.discount(base) for p in self.promotions], default=0)
        member = user.membership_rate()

        coupons = [c.code for c in user.coupons if c.valid()]

        return {
            "items": [
                {"id": i.get_id(),
                 "type": i.__class__.__name__, 
                 "price": i.price}
                for i in booking.get_all_items()
            ],
            "base_price": base,
            "promotion_discount": promo,
            "membership_rate": member,
            "available_coupons": coupons
        }

    # STEP 2 : pay
    def pay(self, user, booking, coupon_code, slip):

        base = booking.base_price()
        promo = max([p.discount(base) for p in self.promotions], default=0)
        member = user.membership_rate()

        # coupon
        coupon_value = 0
        used = None
        for c in user.coupons:
            if c.code == coupon_code and c.valid():
                coupon_value = c.discount
                used = c
                break

        final = Payment.calculate(base, promo, member, coupon_value)

        # verify bank
        if not Bank.verify(slip):
            raise HTTPException(400, "Transfer failed")

        # update booking status
        booking.payment_status = "deposit_paid"

        # reserve resources
        for r in booking.residence:
            r.reserve()
        for v in booking.vehicle:
            v.reserve()
        for a in booking.activity:
            a.reserve()

        # mark coupon used
        if used:
            used.used = True

        return Payment.receipt(booking.get_all_items(), final)


# ================= MOCK DATA =================
system = System()
users = {}
bookings = {}

# ----- user -----
u = User(
    "U001",
    "silver",
    [
        Coupon("DISC10", 100, date(2026, 12, 31)),
        Coupon("DISC50", 50, date(2026, 12, 31))
    ]
)
users[u.user_id] = u

# ----- booking -----
b = Booking("B001", u)

b.residence.append(Residencebooking("H1", 2000))
b.vehicle.append(Vehiclebooking("V1", 1500))
b.activity.append(Activitybooking("A1", 1000))

bookings[b.booking_id] = b

# ----- promotion -----
system.promotions.append(
    Promotion(0.1, 1000, date(2026, 12, 31))
)


# ---------------- REQUEST MODELS ----------------
class PreviewReq(BaseModel):
    user_id: str
    booking_id: str

class PayReq(BaseModel):
    user_id: str
    booking_id: str
    coupon: str | None = None
    slip: str


# ---------------- API ----------------
@app.post("/preview")
def preview(data: PreviewReq):
    if data.user_id not in users:
        raise HTTPException(404, "User not found")
    if data.booking_id not in bookings:
        raise HTTPException(404, "Booking not found")

    return system.preview(users[data.user_id], bookings[data.booking_id])


@app.post("/pay")
def pay(data: PayReq):
    if data.user_id not in users:
        raise HTTPException(404, "User not found")
    if data.booking_id not in bookings:
        raise HTTPException(404, "Booking not found")

    return system.pay(
        users[data.user_id],
        bookings[data.booking_id],
        data.coupon,
        data.slip
    )