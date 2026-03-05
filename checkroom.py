class DamageItem:
    def __init__(self, damage_id, description, price):
        self._damage_id = damage_id
        self._description = description
        self._price = price

    @property
    def damage_id(self):
        return self._damage_id

    def get_damage_detail(self):
        return {
            "damage_id": self._damage_id,
            "description": self._description,
            "price": self._price
        }


class Room:
    def __init__(self, room_id):
        self._room_id = room_id
        self._status = "available"

    @property
    def room_id(self):
        return self._room_id

    @property
    def status(self):
        return self._status

    def update_status(self, status):
        self._status = status
        return "status_updated"


class ResidenceBooking:
    def __init__(self, residence_booking_id, room: Room):
        self._residence_booking_id = residence_booking_id
        self._room = room

    @property
    def room(self):
        return self._room

    def get_detail(self):
        return self._room.room_id


class Booking:
    def __init__(self, booking_id, residence_booking: ResidenceBooking):
        self._booking_id = booking_id
        self._status = "active"
        self._residence_booking = residence_booking
        self._damage_list = []

    @property
    def booking_id(self):
        return self._booking_id

    @property
    def residence_booking(self):
        return self._residence_booking

    def get_booking_item(self):
        return self

    def update_status(self, status):
        self._status = status
        return "booking updated"

    def add_damage(self, damage: DamageItem):
        self._damage_list.append(damage)
        return "damage recorded"


class System:
    def __init__(self):
        self._bookings = {}
        self._damages = {}

    # ---------- Data Management ----------
    def add_booking(self, booking: Booking):
        self._bookings[booking.booking_id] = booking

    def add_damage_item(self, damage: DamageItem):
        self._damages[damage.damage_id] = damage

    def _get_booking(self, booking_id):
        return self._bookings.get(booking_id)

    def _get_damage(self, damage_id):
        return self._damages.get(damage_id)

    # ---------- Sequence Flow ----------
    def startRoomInspection(self, booking_id):
        booking = self._get_booking(booking_id)
        if not booking:
            return "Booking not found"

        booking.get_booking_item()

        residence_booking = booking.residence_booking
        room_id = residence_booking.get_detail()

        residence_booking.room.update_status("checking")

        return f"inspection started + room_id {room_id}"

    def addDamage(self, booking_id, damage_id):
        booking = self._get_booking(booking_id)
        damage = self._get_damage(damage_id)

        if not booking or not damage:
            return "Error"

        damage.get_damage_detail()
        booking.add_damage(damage)

        return "damage added"

    def confirmInspectionComplete(self, booking_id, damaged=False):
        booking = self._get_booking(booking_id)
        if not booking:
            return "Booking not found"

        room = booking.residence_booking.room
        room.update_status("Inspected")

        if damaged:
            booking.update_status("wait_damage_payment")
        else:
            booking.update_status("wait_checkout_payment")

        return "inspection finished"

# สร้าง object
room1 = Room("R101")
res_booking = ResidenceBooking("RB01", room1)
booking1 = Booking("B001", res_booking)

damage1 = DamageItem("D01", "Broken Lamp", 500)

# สร้างระบบ
system = System()
system.add_booking(booking1)
system.add_damage_item(damage1)

# เริ่มตรวจ
print(system.startRoomInspection("B001"))

# ถ้ามีความเสียหาย
print(system.addDamage("B001", "D01"))

# ยืนยันผล (กรณีมี damage)
print(system.confirmInspectionComplete("B001", damaged=True))