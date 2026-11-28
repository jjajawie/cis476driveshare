import hashlib
import sqlite3

#Manages SQLite database connections and table definitions
class DatabaseManager:
    def __init__(self, db_name="driveshare.db"):
        self.conn = sqlite3.connect(db_name)
        self.conn.row_factory = sqlite3.Row
        self.create_tables()

    def create_tables(self):
        #Creates all tables supporting registration, listings, bookings, watches, messages, and alerts
        cur = self.conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 1000.0,
                q1_prompt TEXT NOT NULL,
                q1_answer_hash TEXT NOT NULL,
                q2_prompt TEXT NOT NULL,
                q2_answer_hash TEXT NOT NULL,
                q3_prompt TEXT NOT NULL,
                q3_answer_hash TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cars (
                car_id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                model TEXT NOT NULL,
                year INTEGER NOT NULL,
                mileage INTEGER NOT NULL,
                pickup_location TEXT NOT NULL,
                daily_price REAL NOT NULL,
                avail_start TEXT NOT NULL,
                avail_end TEXT NOT NULL,
                is_available INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (owner_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS bookings (
                booking_id INTEGER PRIMARY KEY AUTOINCREMENT,
                car_id INTEGER NOT NULL,
                renter_id INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                total_amount REAL NOT NULL,
                FOREIGN KEY (car_id) REFERENCES cars(car_id),
                FOREIGN KEY (renter_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS watches (
                watch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                car_id INTEGER NOT NULL,
                renter_id INTEGER NOT NULL,
                max_price REAL NOT NULL,
                notify_on_available INTEGER NOT NULL DEFAULT 1,
                FOREIGN KEY (car_id) REFERENCES cars(car_id),
                FOREIGN KEY (renter_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (sender_id) REFERENCES users(user_id),
                FOREIGN KEY (receiver_id) REFERENCES users(user_id)
            );

            CREATE TABLE IF NOT EXISTS notifications (
                notif_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            );
            """
        )
        self.conn.commit()
   
    def get_sync_signature(self, user_id: int | None):
        cur = self.conn.cursor()
        max_car = cur.execute("SELECT COALESCE(MAX(car_id), 0), COUNT(*) FROM cars").fetchone()
        car_state = cur.execute("SELECT COALESCE(GROUP_CONCAT(car_id || ':' || daily_price || ':' || is_available), '') FROM cars").fetchone()[0]
        max_booking = cur.execute("SELECT COALESCE(MAX(booking_id), 0) FROM bookings").fetchone()[0]
        max_msg = cur.execute("SELECT COALESCE(MAX(message_id), 0) FROM messages").fetchone()[0]
        max_notif = cur.execute("SELECT COALESCE(MAX(notif_id), 0) FROM notifications").fetchone()[0]

        bal = 0.0
        user_cnt = cur.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if user_id is not None:
            row = cur.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if row:
                bal = row["balance"]

        return (max_car[0], max_car[1], car_state, max_booking, max_msg, max_notif, user_cnt, bal)     

    @staticmethod
    #Normalizes and hashes security answers using SHA-256
    def hash_text(raw: str) -> str:
        return hashlib.sha256(raw.strip().lower().encode("utf-8")).hexdigest()

    @staticmethod
    #Hashes user passwords using SHA-256
    def hash_password(password: str) -> str:
        return hashlib.sha256(password.encode("utf-8")).hexdigest()



