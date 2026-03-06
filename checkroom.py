#checkroom

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class DamageItem:
    def __init__(self, damage_id, description, price):
        self.__damage_id = damage_id
        self.__description = description
        self.__price = price

    @property
    def damage_id(self):
        return self.__damage_id

    def get_damage_detail(self):
        return {
            "damage_id": self.__damage_id,
            "description": self.__description,
            "price": self.__price
        }

class Room:
    def __init__(self, room_id):
        self.__room_id = room_id
        self.__status = "available"

    @property
    def room_id(self):
        return self.__room_id

    @property
    def status(self):
        return self.__status

    def update_status(self, status):
        self.__status = status
        return self.__status

class ResidenceBooking:
    def __init__(self, residence_booking_id, room: Room):
        self.__residence_booking_id = residence_booking_id
        self.__room = room

    @property
    def room(self):
        return self.__room

    def start_room_check(self):
        self.__room.update_status("checking")
        return "room checking started"

    def get_detail(self):
        return {
            "residence_booking_id": self.__residence_booking_id,
            "room_id": self.__room.room_id
        }


class Booking:
    def __init__(self, booking_id, residence_booking: ResidenceBooking):
        self.__booking_id = booking_id
        self.__status = "active"
        self.__residence_booking = residence_booking
        self.__damage_list = []

    @property
    def booking_id(self):
        return self.__booking_id

    def get_booking_item(self):
        return self.__residence_booking.get_detail()
    
    def start_room_inspection(self):
        return self.__residence_booking.start_room_check()

    def update_status(self, status):
        self.__status = status
        return self.__status

    def add_damage(self, damage_id, description, price):
        damage = DamageItem(damage_id, description, price)
        self.__damage_list.append(damage)
        return damage.get_damage_detail()


class System:
    def __init__(self):
        self.__bookings = {}

    def add_booking(self, booking: Booking):
        self.__bookings[booking.booking_id] = booking

    def _get_booking(self, booking_id):
        return self.__bookings.get(booking_id)

    def start_room_inspection(self, booking_id):
        booking = self._get_booking(booking_id)

        if not booking:
            return {"error": "Booking not found"}

        return {"message": booking.start_room_inspection()}

    def add_damage(self, booking_id, damage_id, description, price):
        booking = self._get_booking(booking_id)

        if not booking:
            return {"error": "Booking not found"}

        damage = booking.add_damage(damage_id, description, price)
        return {"damage_recorded": damage}

    def confirm_inspection_complete(self, booking_id, damaged=False):
        booking = self._get_booking(booking_id)

        if not booking:
            return {"error": "Booking not found"}

        if damaged:
            booking.update_status("wait_damage_payment")
        else:
            booking.update_status("wait_checkout_payment")

        return {"message": "inspection finished"}


# ------------------ SYSTEM INIT ------------------

system = System()

room1 = Room("R101")
res_booking = ResidenceBooking("RB01", room1)
booking1 = Booking("B001", res_booking)

system.add_booking(booking1)

# ------------------ REQUEST MODEL ------------------

class StartInspectionRequest(BaseModel):
    booking_id: str


class DamageRequest(BaseModel):
    booking_id: str
    damage_id: str
    description: str
    price: float


class CompleteInspectionRequest(BaseModel):
    booking_id: str
    damaged: bool


# ------------------ API ------------------

@app.post("/inspection/start")
def start_inspection(data: StartInspectionRequest):
    return system.start_room_inspection(data.booking_id)


@app.post("/inspection/damage")
def add_damage(data: DamageRequest):
    return system.add_damage(
        data.booking_id,
        data.damage_id,
        data.description,
        data.price
    )


@app.post("/inspection/complete")
def complete_inspection(data: CompleteInspectionRequest):
    return system.confirm_inspection_complete(
        data.booking_id,
        data.damaged
    )