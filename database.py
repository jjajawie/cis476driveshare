import hashlib
import sqlite3
DB_FILE = "driveshare.db"

class DatabaseManager:
    #Manages SQLite database connections and table definitions

    def __init__(self, db_path: str = DB_FILE):
        self.conn = sqlite3.connect(db_path)
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
                full_name TEXT NOT NULL,
                balance REAL NOT NULL DEFAULT 500.0,
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
                car_type TEXT DEFAULT 'Sedan',
                features TEXT DEFAULT '',
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
                status TEXT NOT NULL DEFAULT 'Confirmed',
                is_paid INTEGER NOT NULL DEFAULT 0,
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
                car_id INTEGER,
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

    @staticmethod
    def hash_text(raw: str) -> str:
        #Normalizes and hashes security answers using SHA-256
        return hashlib.sha256(raw.strip().lower().encode("utf-8")).hexdigest()

    @staticmethod
    def hash_password(raw: str) -> str:
        #Hashes user passwords using SHA-256
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

