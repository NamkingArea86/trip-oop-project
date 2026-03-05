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

    # UML: calculate_membership(user_id)
    def calculate_membership(self, user_id):
        return {"gold": 0.2, "silver": 0.1}.get(self.level, 0)

    # UML: get_coupon_list(user_id)
    def get_coupon_list(self, user_id):
        return [c.code for c in self.coupons if c.validate_coupon(c.code)]


# ---------------- COUPON ----------------
class Coupon:
    def __init__(self, code, discount, expiry):
        self.code = code
        self.discount = discount
        self.expiry = expiry
        self.used = False

    # UML: validate_coupon(coupon_code)
    def validate_coupon(self, coupon_code):
        return (
            self.code == coupon_code
            and not self.used
            and date.today() <= self.expiry
        )


# ---------------- PROMOTION ----------------
class Promotion:
    def __init__(self, rate, min_price, expiry):
        self.rate = rate
        self.min_price = min_price
        self.expiry = expiry

    # UML: get_valid_promotion(base_price)
    def get_valid_promotion(self, base_price):
        if base_price >= self.min_price and date.today() <= self.expiry:
            return base_price * self.rate
        return 0


# ---------------- RESIDENCE BOOKING ----------------
class Residencebooking:
    def __init__(self, residence_id, price, start_date=None, end_date=None):
        self.residence_id = residence_id
        self.price = price
        self.start_date = start_date
        self.end_date = end_date
        self.status = "pending"
        self.paid = False

    def get_detail(self, residence_id):
        if residence_id == self.residence_id:
            return self
        return None

    def update_status(self, status):
        self.status = status

    def mark_paid(self):
        self.paid = True

    def get_id(self):
        return self.residence_id


# ---------------- VEHICLE BOOKING ----------------
class Vehiclebooking:
    def __init__(self, vehicle_id, price):
        self.vehicle_id = vehicle_id
        self.price = price
        self.status = "pending"
        self.paid = False

    def get_detail(self, vehicle_id):
        if vehicle_id == self.vehicle_id:
            return self
        return None

    def update_status(self, status):
        self.status = status

    def mark_paid(self):
        self.paid = True

    def get_id(self):
        return self.vehicle_id


# ---------------- ACTIVITY BOOKING ----------------
class Activitybooking:
    def __init__(self, activity_id, price, start_datetime=None, end_datetime=None):
        self.activity_id = activity_id
        self.price = price
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self.status = "pending"
        self.paid = False

    def get_detail(self, activity_id):
        if activity_id == self.activity_id:
            return self
        return None

    def update_status(self, status):
        self.status = status

    def mark_paid(self):
        self.paid = True

    def get_id(self):
        return self.activity_id


# ---------------- BOOKING ----------------
class Booking:
    def __init__(self, booking_id, user):
        self.booking_id = booking_id
        self.user = user
        self.residence = []
        self.vehicle = []
        self.activity = []
        self.status = "unpaid"

    # UML: get_unpaid_items(user_id, booking_id)
    def get_unpaid_items(self, user_id, booking_id):
        items = self.residence + self.vehicle + self.activity
        unpaid = []

        for i in items:
            if not i.paid:
                detail = i.get_detail(i.get_id())
                if detail:
                    unpaid.append(detail)

        price = sum(i.price for i in unpaid)
        return unpaid, price

    # UML: calculate_price(...)
    def calculate_price(self, base_price, promotion_discount, membership_discount, coupon_discount):
        total = base_price - promotion_discount
        total -= total * membership_discount
        total -= coupon_discount
        return max(total, 0)

    # UML: mark_items_paid(item_list)
    def mark_items_paid(self, item_list):
        for i in item_list:
            i.mark_paid()
            i.update_status("reserved")

        if all(i.paid for i in (self.residence + self.vehicle + self.activity)):
            self.status = "fully_paid"
        else:
            self.status = "partially_paid"


# ---------------- PAYMENT ----------------
class Payment:

    # UML: generate_receipt(item_list, final_amount)
    @staticmethod
    def generate_receipt(items, amount):
        return {
            "items": [
                {
                    "id": i.get_id(),
                    "type": i.__class__.__name__,
                    "price": i.price
                }
                for i in items
            ],
            "amount": round(amount, 2)
        }


# ---------------- BANK ----------------
class Bank:

    # UML: verify_transfer(slip_no)
    @staticmethod
    def verify_transfer(slip_no):
        return slip_no and slip_no.startswith("OK")


# ---------------- SYSTEM ----------------
class System:

    def __init__(self):
        self.promotions = []

    # UML: request_payment(user_id, booking_id)
    def request_payment(self, user, booking):

        items, base = booking.get_unpaid_items(user.user_id, booking.booking_id)

        promo = max(
            [p.get_valid_promotion(base) for p in self.promotions],
            default=0
        )

        member = user.calculate_membership(user.user_id)
        coupons = user.get_coupon_list(user.user_id)

        return {
            "unpaid_items": [
                {
                    "id": i.get_id(),
                    "type": i.__class__.__name__,
                    "price": i.price
                }
                for i in items
            ],
            "unpaid_price": base,
            "promotion_discount": promo,
            "membership_discount": member,
            "available_coupons": coupons
        }

    # UML: submit_slip_number(...)
    def submit_slip_number(self, user, booking, coupon_code, slip_no):

        items, base = booking.get_unpaid_items(user.user_id, booking.booking_id)

        if base == 0:
            raise HTTPException(400, "Nothing to pay")

        promo = max(
            [p.get_valid_promotion(base) for p in self.promotions],
            default=0
        )

        member = user.calculate_membership(user.user_id)

        coupon_value = 0
        used_coupon = None

        for c in user.coupons:
            if coupon_code and c.validate_coupon(coupon_code):
                coupon_value = c.discount
                used_coupon = c
                break

        final_price = booking.calculate_price(
            base,
            promo,
            member,
            coupon_value
        )

        if not Bank.verify_transfer(slip_no):
            raise HTTPException(400, "Transfer failed")

        booking.mark_items_paid(items)

        if used_coupon:
            used_coupon.used = True

        return Payment.generate_receipt(items, final_price)


# ================= MOCK DATA =================
system = System()
users = {}
bookings = {}

u = User(
    "U001",
    "silver",
    [
        Coupon("DISC10", 100, date(2026, 12, 31)),
        Coupon("DISC50", 50, date(2026, 12, 31))
    ]
)

users[u.user_id] = u

b = Booking("B001", u)
b.residence.append(Residencebooking("HOTEL1", 2000))

bookings[b.booking_id] = b

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
@app.post("/request_payment")
def request_payment(data: PreviewReq):

    if data.user_id not in users:
        raise HTTPException(404, "User not found")

    if data.booking_id not in bookings:
        raise HTTPException(404, "Booking not found")

    return system.request_payment(
        users[data.user_id],
        bookings[data.booking_id]
    )


@app.post("/submit_slip_number")
def submit_slip_number(data: PayReq):

    if data.user_id not in users:
        raise HTTPException(404, "User not found")

    if data.booking_id not in bookings:
        raise HTTPException(404, "Booking not found")

    return system.submit_slip_number(
        users[data.user_id],
        bookings[data.booking_id],
        data.coupon,
        data.slip
    )