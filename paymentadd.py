from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

# ================= SYSTEM STORAGE =================
class System:
    def __init__(self):
        self.members = {}
        self.resources = {}
        self.bookings = {}
        self.transactions = {}

SYSTEM = System()

# ================= MODELS =================
class MemberCreate(BaseModel):
    name: str

class PayRequest(BaseModel):
    use_coupon: bool = False
    use_points: bool = False
    points_to_use: int = 0

# ================= ENTITIES =================
class Member:
    counter = 1
    def __init__(self, name):
        self.id = f"M{Member.counter:03d}"
        Member.counter += 1
        self.name = name
        self.points = 100
        self.discount_rate = 0.1

    def add_point(self, amount):
        self.points += int(amount / 10)


class Resource:
    counter = 1
    def __init__(self, name, price):
        self.id = f"R{Resource.counter:03d}"
        Resource.counter += 1
        self.name = name
        self.price = price
        self.status = "AVAILABLE"


class Booking:
    counter = 1
    def __init__(self, member):
        self.id = f"B{Booking.counter:03d}"
        Booking.counter += 1
        self.member = member
        self.resources = []
        self.status = "CREATED"

    def add_resource(self, resource):
        self.resources.append(resource)

    def calculate_price(self):
        return sum(r.price for r in self.resources)

    def set_paid(self):
        self.status = "PAID"


class Payment:
    counter = 1
    def __init__(self, booking, price):
        self.id = f"P{Payment.counter:03d}"
        Payment.counter += 1
        self.booking = booking
        self.final_price = price

    def apply_membership_discount(self, rate):
        self.final_price *= (1 - rate)

    def apply_coupon(self):
        self.final_price *= 0.8

    def apply_promotion(self):
        self.final_price *= 0.9

    def apply_points(self, points):
        self.final_price -= points


class Transaction:
    counter = 1
    def __init__(self, amount):
        self.id = f"T{Transaction.counter:03d}"
        Transaction.counter += 1
        self.amount = amount
        self.status = "PENDING"

    def approve(self):
        self.status = "APPROVED"


class Staff:
    def verify_payment(self, transaction: Transaction):
        transaction.approve()
        return True


class Manager:
    def verify_payment(self, transaction: Transaction):
        return True

# ================= SEED RESOURCES =================
def seed_resources():
    # rooms
    for _ in range(10):
        r = Resource("Hotel Room Normal", 1200)
        SYSTEM.resources[r.id] = r
    for _ in range(10):
        r = Resource("Hotel Room King", 1800)
        SYSTEM.resources[r.id] = r
    for _ in range(5):
        r = Resource("Pool Villa", 4500)
        SYSTEM.resources[r.id] = r

    # vehicles
    for _ in range(10):
        r = Resource("Car", 900)
        SYSTEM.resources[r.id] = r
    for _ in range(10):
        r = Resource("Motorcycle", 400)
        SYSTEM.resources[r.id] = r

seed_resources()

# ================= API =================

@app.get("/")
def root():
    return {"message": "Travel booking system running"}

# ---------- CREATE MEMBER ----------
@app.post("/members")
def create_member(data: MemberCreate):
    m = Member(data.name)
    SYSTEM.members[m.id] = m
    return {"member_id": m.id, "name": m.name, "points": m.points}

# ---------- CREATE BOOKING ----------
@app.post("/booking/create/{member_id}")
def create_booking(member_id: str):
    member = SYSTEM.members.get(member_id)
    if not member:
        raise HTTPException(404, "Member not found")

    booking = Booking(member)
    SYSTEM.bookings[booking.id] = booking

    return {"booking_id": booking.id, "status": booking.status}

# ---------- ADD RESOURCE TO BOOKING ----------
@app.post("/booking/{booking_id}/add/{resource_id}")
def add_resource(booking_id: str, resource_id: str):

    booking = SYSTEM.bookings.get(booking_id)
    resource = SYSTEM.resources.get(resource_id)

    if not booking:
        raise HTTPException(404, "Booking not found")
    if not resource:
        raise HTTPException(404, "Resource not found")

    booking.add_resource(resource)

    return {
        "booking_id": booking.id,
        "added": resource.name,
        "items": len(booking.resources)
    }

# ---------- PAY BOOKING ----------
@app.post("/pay/{booking_id}")
def pay_booking(booking_id: str, req: PayRequest):

    booking = SYSTEM.bookings.get(booking_id)
    if not booking:
        raise HTTPException(404, "Booking not found")

    base_price = booking.calculate_price()
    if base_price == 0:
        raise HTTPException(400, "No items in booking")

    payment = Payment(booking, base_price)

    payment.apply_membership_discount(booking.member.discount_rate)
    payment.apply_promotion()

    if req.use_coupon:
        payment.apply_coupon()

    if req.use_points:
        if req.points_to_use > booking.member.points:
            raise HTTPException(400, "Not enough points")
        payment.apply_points(req.points_to_use)
        booking.member.points -= req.points_to_use

    if payment.final_price < 0:
        payment.final_price = 0

    transaction = Transaction(payment.final_price)

    staff = Staff()
    manager = Manager()

    if not staff.verify_payment(transaction):
        raise HTTPException(400, "Staff rejected")
    if not manager.verify_payment(transaction):
        raise HTTPException(400, "Manager rejected")

    booking.set_paid()
    booking.member.add_point(transaction.amount)

    SYSTEM.transactions[transaction.id] = transaction.amount

    return {
        "booking_id": booking.id,
        "transaction_id": transaction.id,
        "status": booking.status,
        "final_price": round(transaction.amount,2),
        "member_points": booking.member.points
    }
