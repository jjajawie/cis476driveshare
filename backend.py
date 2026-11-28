import hashlib
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime
from database import DatabaseManager

#SINGLETON
class SessionManager:
    #Maintains a single active session state across the application
    instance = None

    def __new__(cls):
        if cls.instance is None:
            cls.instance = super(SessionManager, cls).__new__(cls)
            cls.instance.current_user = None
            cls.instance.session_token = None
        return cls.instance

    def login(self, user_row: sqlite3.Row):
        #Authenticates a user and generates a session token
        self.current_user = dict(user_row)
        #Manages the users tokenn and hashes is using SHA256
        token_seed = f"{user_row['user_id']}:{user_row['email']}:{datetime.now().isoformat()}"
        self.session_token = hashlib.sha256(token_seed.encode("utf-8")).hexdigest()[:24]

    def logout(self):
        #Clears active user session
        self.current_user = None
        self.session_token = None

    def refresh_user(self, db: DatabaseManager):
        #Refreshes active user fields (such as balance) from SQLite
        if not self.current_user:
            return
        current = db.conn.cursor()
        current.execute("SELECT * FROM users WHERE user_id = ?", (self.current_user["user_id"],))
        row = current.fetchone()
        if row:
            self.current_user = dict(row)

    @property
    def is_authenticated(self) -> bool:
        return self.current_user is not None and self.session_token is not None



#CHAIN OF RESPONSIBILITY
class SecurityQuestionHandler(ABC):
    #Base handler for sequential security question verification
    def __init__(self):
        self.next_handler = None

    def set_next(self, handler):
        self.next_handler = handler
        return handler

    @abstractmethod
    def handle(self, user_record: dict, answers: list):
        pass


class FirstQuestionHandler(SecurityQuestionHandler):
    #Checks answer #1 before delegating down the chain
    def handle(self, user_record: dict, answers: list):
        if DatabaseManager.hash_text(answers[0]) != user_record["q1_answer_hash"]:
            return False, "Answer is incorrect"
        if self.next_handler:
            return self.next_handler.handle(user_record, answers)
        return True, "Correct"


class SecondQuestionHandler(SecurityQuestionHandler):
    #Checks answer #2 before delegating down the chain
    def handle(self, user_record: dict, answers: list):
        if DatabaseManager.hash_text(answers[1]) != user_record["q2_answer_hash"]:
            return False, "Answer is incorrect."
        if self.next_handler:
            return self.next_handler.handle(user_record, answers)
        return True, "Correct"


class ThirdQuestionHandler(SecurityQuestionHandler):
    #Checks answer #3 at the end of the verification chain
    def handle(self, user_record: dict, answers: list):
        if DatabaseManager.hash_text(answers[2]) != user_record["q3_answer_hash"]:
            return False, "Security Question 3 answer is incorrect."
        return True, "All questions verified successfully."

# BUILDER
class Listing:
    #Constructed vehicle listing entity
    def __init__(self):
        self.owner_id = None
        self.model = ""
        self.year = 2026
        self.mileage = 0
        self.pickup_location = ""
        self.daily_price = 0.0
        self.avail_start = ""
        self.avail_end = ""
        self.is_available = 1


class ListingBuilder:
    #Fluent builder for assembling and validating Listing objects
    def __init__(self):
        self.car = Listing()

    def set_owner(self, owner_id: int):
        self.car.owner_id = owner_id
        return self

    def set_vehicle_info(self, model: str, year: int, mileage: int):
        self.car.model = model.strip()
        self.car.year = year
        self.car.mileage = mileage
        return self

    def set_rental_terms(self, location: str, daily_price: float, avail_start: str, avail_end: str):
        self.car.pickup_location = location.strip()
        self.car.daily_price = daily_price
        self.car.avail_start = avail_start.strip()
        self.car.avail_end = avail_end.strip()
        return self

    def build(self) -> Listing:
        #Validates required fields and date ranges before returning Listing.
        if not self.car.model or not self.car.pickup_location:
            raise ValueError("Model and Pickup Location are required.")
        if self.car.mileage < 0:
            raise ValueError("Mileage cannot be negative.")
        if self.car.daily_price <= 0:
            raise ValueError("Daily price must be greater than $0.")
        
        #sets the time for how long the car is available
        datetime.strptime(self.car.avail_start, "%Y-%m-%d")
        datetime.strptime(self.car.avail_end, "%Y-%m-%d")
        
        if self.car.avail_start > self.car.avail_end:
            raise ValueError("Availability start date must be on or before end date.")
        return self.car



#OBSERVER
class Observer(ABC):
    #Observer interface for watch alerts
    @abstractmethod
    def update(self, car_data: dict, reason: str):
        pass


class RenterObserver(Observer):
    #Notifies a watching renter when price drops or its available.

    def __init__(self, db: DatabaseManager, renter_id: int, max_price: float, notify_avail: bool):
        self.db = db
        self.renter_id = renter_id
        self.max_price = max_price
        self.notify_avail = notify_avail

    def update(self, car_data: dict, reason: str):
        price_match = car_data["daily_price"] <= self.max_price
        avail_match = self.notify_avail and bool(car_data["is_available"])
        if price_match or avail_match:
            status_text = "Available" if car_data["is_available"] else "Unavailable"
            message = (
                #sends a message on updates to the car
                f"[Watch Alert] {car_data['model']} ({car_data['pickup_location']}) "
                f"is now ${car_data['daily_price']:.2f}/day ({status_text}) - {reason}"
            )
            current = self.db.conn.cursor()
            current.execute(
                "INSERT INTO notifications (user_id, message, created_at) VALUES (?, ?, ?)",
                (self.renter_id, message, datetime.now().strftime("%Y-%m-%d %H:%M")),
            )
            self.db.conn.commit()


class CarSubject:
    #Subject tracking observers watching a specific car.
    def __init__(self, db: DatabaseManager, car_id: int):
        self.db = db
        self.car_id = car_id
        self._observers: list[RenterObserver] = []
        self.load_observers()

    #sets the person interested
    def load_observers(self):
        current = self.db.conn.cursor()
        current.execute("SELECT * FROM watches WHERE car_id = ?", (self.car_id,))
        for row in current.fetchall():
            self._observers.append(
                RenterObserver(
                    self.db,
                    row["renter_id"],
                    row["max_price"],
                    bool(row["notify_on_available"]),
                )
            )

    #notifies the person interested
    def notify(self, reason: str):
        current = self.db.conn.cursor()
        current.execute("SELECT * FROM cars WHERE car_id = ?", (self.car_id,))
        car = current.fetchone()
        if not car:
            return
        car_data = dict(car)
        for obs in self._observers:
            obs.update(car_data, reason)



#PROXY
class PaymentGateway(ABC):
    #payment interface for proxy and real payment processor
    @abstractmethod
    def process_payment(self, booking_id: int, renter_id: int, amount: float):
        pass


class RealPaymentGateway(PaymentGateway):
    #Executes balance transfer, updates booking payment status, and logs alerts
    def __init__(self, db: DatabaseManager):
        self.db = db

    def process_payment(self, booking_id: int, renter_id: int, amount: float):
        #Handles the processing of the payment
        current = self.db.conn.cursor()
        current.execute(
            """
            SELECT b.*, c.owner_id, c.model
            FROM bookings b
            JOIN cars c ON b.car_id = c.car_id
            WHERE b.booking_id = ?
            """,
            (booking_id,),
        )
        booking = current.fetchone()
        if not booking:
            return False, "Booking not found"

        #In the event the payee has insufficient funds
        current.execute("SELECT balance FROM users WHERE user_id = ?", (renter_id,))
        renter = current.fetchone()
        if renter["balance"] < amount:
            return False, f"Insufficient balance, (${renter['balance']:.2f} available)."

        current.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, renter_id))
        current.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, booking["owner_id"]),
        )

        #to confirm payments on date and time
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        current.execute(
            "INSERT INTO notifications (user_id, message, created_at) VALUES (?, ?, ?)",
            (
                renter_id,
                f"Payment of ${amount:.2f} sent for Booking #{booking_id} ({booking['model']}).",
                now,
            ),
        )
        current.execute(
            "INSERT INTO notifications (user_id, message, created_at) VALUES (?, ?, ?)",
            (
                booking["owner_id"],
                f"Payment of ${amount:.2f} received for Booking #{booking_id} ({booking['model']}).",
                now,
            ),
        )
        self.db.conn.commit()
        return True, f"Payment of ${amount:.2f} processed! Both owner and renter notified."


class PaymentServiceProxy(PaymentGateway):
    #Guards REalPaymentGateway with session, identity, and amount checks
    def __init__(self, db: DatabaseManager, session: SessionManager):
        self.db = db
        self.session = session
        self.real_gateway = RealPaymentGateway(db)
    #Input handling for ensuring proper session and payment is non zero
    def process_payment(self, booking_id: int, renter_id: int, amount: float):
        if not self.session.is_authenticated:
            return False, "Unauthorized: Active session required"
        if self.session.current_user["user_id"] != renter_id:
            return False, "Failed: Session user mismatch"
        if amount <= 0:
            return False, "Payment amount must be greater than $0"
        return self.real_gateway.process_payment(booking_id, renter_id, amount)

#MEDIATOR
class UIMediator:
    #Coordinates navigation and data refreshes across UI components
    def __init__(self):
        self.components = {}

    def register(self, name: str, component):
        self.components[name] = component

    def notify(self, sender: str, event: str, payload=None):
        app = self.components.get("app")
        dashboard = self.components.get("dashboard")
        #Events for when the application is moving from state to state
        if event == "LOGIN_SUCCESS" and app:
            app.show_main_dashboard()
        elif event == "LOGOUT" and app:
            app.show_auth_screen()
        elif event in ("CAR_UPDATED", "BOOKING_CREATED", "PAYMENT_COMPLETED", "MESSAGE_SENT") and dashboard:
            dashboard.refresh_all_tabs()
        elif event == "OPEN_CHAT_WITH_OWNER" and dashboard:
            dashboard.jump_to_messages(payload)