# payment

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import date

app = FastAPI()

# ---------------- USER ----------------
class User:

    def __init__(self, user_id, coupons=None):
        self.__user_id = user_id
        self.__coupons = coupons or []
        self.__total_spent = 0

    def get_user_id(self):
        return self.__user_id

    def get_coupons(self):
        return self.__coupons

    def add_spent(self, amount):
        self.__total_spent += amount

    def calculate_membership(self):
        if self.__total_spent >= 10000:
            return 0.2
        elif self.__total_spent >= 5000:
            return 0.1
        else:
            return 0

    def get_coupon_list(self):
        return [
            c.get_code()
            for c in self.__coupons
            if c.validate_coupon(c.get_code())
        ]


# ---------------- COUPON ----------------
class Coupon:

    def __init__(self, code, discount, expiry):
        self.__code = code
        self.__discount = discount
        self.__expiry = expiry
        self.__used = False

    def get_code(self):
        return self.__code

    def get_discount(self):
        return self.__discount

    def set_used(self, value):
        self.__used = value

    def validate_coupon(self, coupon_code):
        return (
            self.__code == coupon_code
            and not self.__used
            and date.today() <= self.__expiry
        )


# ---------------- PROMOTION ----------------
class Promotion:

    def __init__(self, rate, min_price, expiry):
        self.__rate = rate
        self.__min_price = min_price
        self.__expiry = expiry

    def get_valid_promotion(self, base_price):
        if base_price >= self.__min_price and date.today() <= self.__expiry:
            return base_price * self.__rate
        return 0


# ---------------- RESIDENCE BOOKING ----------------
class Residencebooking:

    def __init__(self, residence_id, price):
        self.__residence_id = residence_id
        self.__price = price
        self.__status = "pending"
        self.__paid = False

    def get_detail(self, residence_id):
        if residence_id == self.__residence_id:
            return self
        return None

    def get_price(self):
        return self.__price

    def get_paid(self):
        return self.__paid

    def update_status(self, status):
        self.__status = status

    def mark_paid(self):
        self.__paid = True

    def get_id(self):
        return self.__residence_id


# ---------------- VEHICLE BOOKING ----------------
class Vehiclebooking:

    def __init__(self, vehicle_id, price):
        self.__vehicle_id = vehicle_id
        self.__price = price
        self.__status = "pending"
        self.__paid = False

    def get_detail(self, vehicle_id):
        if vehicle_id == self.__vehicle_id:
            return self
        return None

    def get_price(self):
        return self.__price

    def get_paid(self):
        return self.__paid

    def update_status(self, status):
        self.__status = status

    def mark_paid(self):
        self.__paid = True

    def get_id(self):
        return self.__vehicle_id


# ---------------- ACTIVITY BOOKING ----------------
class Activitybooking:

    def __init__(self, activity_id, price):
        self.__activity_id = activity_id
        self.__price = price
        self.__status = "pending"
        self.__paid = False

    def get_detail(self, activity_id):
        if activity_id == self.__activity_id:
            return self
        return None

    def get_price(self):
        return self.__price

    def get_paid(self):
        return self.__paid

    def update_status(self, status):
        self.__status = status

    def mark_paid(self):
        self.__paid = True

    def get_id(self):
        return self.__activity_id


# ---------------- BOOKING ----------------
class Booking:

    def __init__(self, booking_id, user):
        self.__booking_id = booking_id
        self.__user = user
        self.__residence = []
        self.__vehicle = []
        self.__activity = []
        self.__status = "unpaid"

    def get_booking_id(self):
        return self.__booking_id

    def get_residence(self):
        return self.__residence

    def get_vehicle(self):
        return self.__vehicle

    def get_activity(self):
        return self.__activity

    def get_unpaid_items(self):

        items = self.__residence + self.__vehicle + self.__activity
        unpaid = [i for i in items if not i.get_paid()]

        price = sum(i.get_price() for i in unpaid)

        return unpaid, price

    def calculate_price(self, base, promo, member, coupon):

        total = base - promo
        total -= total * member
        total -= coupon

        return max(total, 0)

    def mark_items_paid(self, items, final_price):

        for i in items:
            i.mark_paid()
            i.update_status("reserved")

        self.__user.add_spent(final_price)

        if all(i.get_paid() for i in (self.__residence + self.__vehicle + self.__activity)):
            self.__status = "fully_paid"
        else:
            self.__status = "partially_paid"


# ---------------- PAYMENT ----------------
class Payment:

    @staticmethod
    def generate_receipt(items, amount):

        return {
            "items": [
                {
                    "id": i.get_id(),
                    "type": i.__class__.__name__,
                    "price": i.get_price()
                }
                for i in items
            ],
            "amount": round(amount, 2)
        }


# ---------------- BANK ----------------
class Bank:

    @staticmethod
    def verify_transfer(slip):

        return slip and slip.startswith("OK")


# ---------------- SYSTEM ----------------
class System:

    def __init__(self):
        self.__promotions = []
        self.__selected_coupons = {}

    def get_promotions(self):
        return self.__promotions

    def request_payment(self, user, booking):

        items, base = booking.get_unpaid_items()

        promo = max(
            [p.get_valid_promotion(base) for p in self.__promotions],
            default=0
        )

        member = user.calculate_membership()

        return {
            "items": [
                {
                    "id": i.get_id(),
                    "type": i.__class__.__name__,
                    "price": i.get_price()
                }
                for i in items
            ],
            "base_price": base,
            "promotion_discount": promo,
            "membership_discount": member,
            "available_coupons": user.get_coupon_list()
        }

    def select_coupon(self, user, booking, coupon_code):

        items, base = booking.get_unpaid_items()

        promo = max(
            [p.get_valid_promotion(base) for p in self.__promotions],
            default=0
        )

        member = user.calculate_membership()

        coupon_value = 0

        for c in user.get_coupons():
            if coupon_code and c.validate_coupon(coupon_code):
                coupon_value = c.get_discount()
                break

        final_price = booking.calculate_price(
            base,
            promo,
            member,
            coupon_value
        )

        self.__selected_coupons[booking.get_booking_id()] = coupon_code

        return {
            "base_price": base,
            "promotion_discount": promo,
            "membership_discount": member,
            "coupon_discount": coupon_value,
            "final_price": final_price
        }

    def submit_slip_number(self, user, booking, slip):

        items, base = booking.get_unpaid_items()

        if base == 0:
            raise HTTPException(400, "Nothing to pay")

        coupon_code = self.__selected_coupons.get(
            booking.get_booking_id()
        )

        promo = max(
            [p.get_valid_promotion(base) for p in self.__promotions],
            default=0
        )

        member = user.calculate_membership()

        coupon_value = 0
        used_coupon = None

        for c in user.get_coupons():
            if coupon_code and c.validate_coupon(coupon_code):
                coupon_value = c.get_discount()
                used_coupon = c
                break

        final_price = booking.calculate_price(
            base,
            promo,
            member,
            coupon_value
        )

        if not Bank.verify_transfer(slip):
            raise HTTPException(400, "Transfer failed")

        booking.mark_items_paid(items, final_price)

        if used_coupon:
            used_coupon.set_used(True)

        return Payment.generate_receipt(items, final_price)


# ================= MOCK DATA =================
system = System()
users = {}
bookings = {}

u = User(
    "U001",
    [
        Coupon("DISC10", 100, date(2026, 12, 31)),
        Coupon("DISC50", 50, date(2026, 12, 31))
    ]
)

users[u.get_user_id()] = u

b = Booking("B001", u)

b.get_residence().append(
    Residencebooking("HOTEL1", 2000)
)

bookings[b.get_booking_id()] = b

system.get_promotions().append(
    Promotion(0.1, 1000, date(2026, 12, 31))
)


# ---------------- REQUEST MODEL ----------------
class PreviewReq(BaseModel):
    user_id: str
    booking_id: str


class SelectCouponReq(BaseModel):
    user_id: str
    booking_id: str
    coupon: str | None = None


class PayReq(BaseModel):
    user_id: str
    booking_id: str
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


@app.post("/select_coupon")
def select_coupon(data: SelectCouponReq):

    if data.user_id not in users:
        raise HTTPException(404, "User not found")

    if data.booking_id not in bookings:
        raise HTTPException(404, "Booking not found")

    return system.select_coupon(
        users[data.user_id],
        bookings[data.booking_id],
        data.coupon
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
        data.slip
    )