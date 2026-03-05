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

    def update_status(self, status):
        self._status = status
        return "status updated"


class ResidenceBooking:
    def __init__(self, residence_booking_id, room: Room):
        self._residence_booking_id = residence_booking_id
        self._room = room

    @property
    def room(self):
        return self._room

    def get_detail(self):
        # Booking -> ResidenceBooking : get_detail()
        # ResidenceBooking -> Room : update_status("checking")
        self._room.update_status("checking")
        return "room ready"


class Booking:
    def __init__(self, booking_id, residence_booking: ResidenceBooking):
        self._booking_id = booking_id
        self._status = "active"
        self._residence_booking = residence_booking
        self._damage_list = []

    @property
    def booking_id(self):
        return self._booking_id

    def get_booking_item(self, booking_id):
        # System -> Booking : get_booking_item(booking_id)
        if booking_id == self._booking_id:
            self._residence_booking.get_detail()
            return "booking detail"
        return None

    def update_status(self, status):
        self._status = status
        return "booking updated"

    def add_damage(self, damage_id, description, price):
        # Booking -> DamageItem : create damage item
        damage = DamageItem(damage_id, description, price)
        self._damage_list.append(damage)
        return "damage recorded"


class System:
    def __init__(self):
        self._bookings = {}

    def add_booking(self, booking: Booking):
        self._bookings[booking.booking_id] = booking

    def _get_booking(self, booking_id):
        return self._bookings.get(booking_id)

    # ---------- Sequence Flow ----------

    def startRoomInspection(self, booking_id):
        booking = self._get_booking(booking_id)
        if not booking:
            return "Booking not found"

        booking.get_booking_item(booking_id)
        return "inspection started"

    def addDamage(self, booking_id, damage_id, description, price):
        booking = self._get_booking(booking_id)
        if not booking:
            return "Booking not found"

        booking.add_damage(damage_id, description, price)
        return "damage added"

    def confirmInspectionComplete(self, booking_id, damaged=False):
        booking = self._get_booking(booking_id)
        if not booking:
            return "Booking not found"

        if damaged:
            booking.update_status("wait_damage_payment")
        else:
            booking.update_status("wait_checkout_payment")

        return "inspection finished"


# ------------------ TEST ------------------

room1 = Room("R101")
res_booking = ResidenceBooking("RB01", room1)
booking1 = Booking("B001", res_booking)

system = System()
system.add_booking(booking1)

print(system.startRoomInspection("B001"))

print(system.addDamage("B001", "D01", "Broken Lamp", 500))

print(system.confirmInspectionComplete("B001", damaged=True))