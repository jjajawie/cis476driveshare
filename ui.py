import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

from database import DatabaseManager
from backend import (
    CarSubject,
    FirstQuestionHandler,
    ListingBuilder,
    PaymentServiceProxy,
    SecondQuestionHandler,
    SessionManager,
    ThirdQuestionHandler,
    UIMediator,
)


# Configures the ttk style for the UI
def UI_Theme(root: tk.Tk):
    root.configure(bg="#f4f6f9")
    style = ttk.Style(root)
    style.theme_use("clam")

    style.configure(".", background="#f4f6f9", foreground="#18202c", font=("Segoe UI", 10))
    style.configure("TFrame", background="#f4f6f9")
    style.configure("Card.TFrame", background="#ffffff")
    style.configure("Header.TFrame", background="#0f172a")

    style.configure("Title.TLabel", background="#f4f6f9", foreground="#18202c", font=("Segoe UI", 20, "bold"))
    style.configure("Field.TLabel", background="#ffffff", foreground="#18202c", font=("Segoe UI", 9, "bold"))
    style.configure("Muted.TLabel", background="#ffffff", foreground="#5a6778", font=("Segoe UI", 9))
    style.configure("Banner.TLabel", background="#0f172a", foreground="#ffffff", font=("Segoe UI", 10, "bold"))

    style.configure("TEntry", fieldbackground="#f8fafc", foreground="#18202c", padding=5)
    style.configure("TCombobox", fieldbackground="#f8fafc", foreground="#18202c", padding=4)

    style.configure("TNotebook.Tab", background="#e2e8f0", foreground="#334155", padding=[12, 7], font=("Segoe UI", 9, "bold"))
    style.map("TNotebook.Tab", background=[("selected", "#ffffff")], foreground=[("selected", "#2563eb")])

    style.configure("Primary.TButton", background="#2563eb", foreground="#ffffff", padding=[10, 6], font=("Segoe UI", 9, "bold"))
    style.map("Primary.TButton", background=[("active", "#1d4ed8")])

    style.configure("Secondary.TButton", background="#e2e8f0", foreground="#18202c", padding=[10, 6], font=("Segoe UI", 9))
    style.map("Secondary.TButton", background=[("active", "#cbd5e1")])

    style.configure("Treeview", background="#ffffff", foreground="#18202c", fieldbackground="#ffffff", rowheight=26, font=("Segoe UI", 9))
    style.configure("Treeview.Heading", background="#e2e8f0", foreground="#18202c", font=("Segoe UI", 9, "bold"))


class AuthFrame(ttk.Frame):
    # Registration (with 3 security questions), login, and password recovery
    def __init__(self, parent, db: DatabaseManager, session: SessionManager, mediator: UIMediator):
        super().__init__(parent, padding=24)
        self.db, self.session, self.mediator = db, session, mediator

        box = ttk.Frame(self)
        box.place(relx=0.5, rely=0.5, anchor="center", width=480, height=540)
        ttk.Label(box, text="DriveShare", style="Title.TLabel").pack(anchor="w", pady=(0, 10))

        notebook = ttk.Notebook(box)
        notebook.pack(fill="both", expand=True)

        login_tab = ttk.Frame(notebook, style="Card.TFrame", padding=18)
        reg_tab = ttk.Frame(notebook, style="Card.TFrame", padding=16)
        rec_tab = ttk.Frame(notebook, style="Card.TFrame", padding=16)

        notebook.add(login_tab, text="Login")
        notebook.add(reg_tab, text="Register")
        notebook.add(rec_tab, text="Recover Password")

        self.build_login(login_tab)
        self.build_register(reg_tab)
        self.build_recover(rec_tab)

    def build_login(self, parent):
        ttk.Label(parent, text="Email", style="Field.TLabel").pack(anchor="w")
        self.login_email = ttk.Entry(parent)
        self.login_email.pack(fill="x", pady=(3, 10))

        ttk.Label(parent, text="Password", style="Field.TLabel").pack(anchor="w")
        self.login_pw = ttk.Entry(parent, show="*")
        self.login_pw.pack(fill="x", pady=(3, 14))

        ttk.Button(parent, text="Login", style="Primary.TButton", command=self.handle_login).pack(fill="x")

    def build_register(self, parent):
        canvas = tk.Canvas(parent, bg="#ffffff", highlightthickness=0)
        sb = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        form = ttk.Frame(canvas, style="Card.TFrame")
        form.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=form, anchor="nw", width=405)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        fields = [
            ("Email", "reg_email", False),
            ("Password", "reg_pw", True),
            ("Security Question 1", "reg_q1", False),
            ("Answer 1", "reg_a1", False),
            ("Security Question 2", "reg_q2", False),
            ("Answer 2", "reg_a2", False),
            ("Security Question 3", "reg_q3", False),
            ("Answer 3", "reg_a3", False),
        ]
        for lbl, attr, secret in fields:
            ttk.Label(form, text=lbl, style="Field.TLabel").pack(anchor="w", pady=(5, 2))
            ent = ttk.Entry(form, show="*" if secret else "")
            ent.pack(fill="x")
            setattr(self, attr, ent)

        ttk.Button(form, text="Register", style="Primary.TButton", command=self.handle_register).pack(fill="x", pady=(12, 2))

    def build_recover(self, parent):
        ttk.Label(parent, text="Email", style="Field.TLabel").pack(anchor="w")
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=(3, 8))
        self.rec_email = ttk.Entry(row)
        self.rec_email.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(row, text="Load Questions", style="Secondary.TButton", command=self.load_recovery_questions).pack(side="right")

        self.q_labels = []
        self.rec_answers = []
        for idx in range(3):
            ql = ttk.Label(parent, text=f"Question {idx + 1}: -", style="Muted.TLabel")
            ql.pack(anchor="w", pady=(4, 2))
            ae = ttk.Entry(parent)
            ae.pack(fill="x", pady=(0, 6))
            self.q_labels.append(ql)
            self.rec_answers.append(ae)

        ttk.Label(parent, text="New Password", style="Field.TLabel").pack(anchor="w")
        self.rec_new_pw = ttk.Entry(parent, show="*")
        self.rec_new_pw.pack(fill="x", pady=(3, 10))

        ttk.Button(parent, text="Reset Password", style="Primary.TButton", command=self.handle_password_reset).pack(fill="x")

    def handle_login(self):
        email = self.login_email.get().strip().lower()
        pw_hash = DatabaseManager.hash_password(self.login_pw.get())
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ? AND password_hash = ?", (email, pw_hash))
        user = cur.fetchone()
        if not user:
            messagebox.showerror("Error", "Invalid email or password.")
            return
        self.session.login(user)
        self.mediator.notify("AuthFrame", "LOGIN_SUCCESS")

    def handle_register(self):
        vals = [
            self.reg_email.get().strip().lower(),
            self.reg_pw.get(),
            self.reg_q1.get().strip(),
            self.reg_a1.get().strip(),
            self.reg_q2.get().strip(),
            self.reg_a2.get().strip(),
            self.reg_q3.get().strip(),
            self.reg_a3.get().strip(),
        ]
        if not all(vals):
            messagebox.showwarning("Error", "Fill out email, password, and all 3 security questions/answers.")
            return
        try:
            cur = self.db.conn.cursor()
            cur.execute(
                """
                INSERT INTO users (email, password_hash, balance, q1_prompt, q1_answer_hash, q2_prompt, q2_answer_hash, q3_prompt, q3_answer_hash)
                VALUES (?, ?, 1000.0, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vals[0],
                    DatabaseManager.hash_password(vals[1]),
                    vals[2],
                    DatabaseManager.hash_text(vals[3]),
                    vals[4],
                    DatabaseManager.hash_text(vals[5]),
                    vals[6],
                    DatabaseManager.hash_text(vals[7]),
                ),
            )
            self.db.conn.commit()
            messagebox.showinfo("Success", "Registered. You can log in now.")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Email already registered.")

    def load_recovery_questions(self):
        email = self.rec_email.get().strip().lower()
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        if not user:
            messagebox.showerror("Error", "User not found.")
            return
        prompts = [user["q1_prompt"], user["q2_prompt"], user["q3_prompt"]]
        for idx, lbl in enumerate(self.q_labels):
            lbl.config(text=f"Question {idx + 1}: {prompts[idx]}")

    def handle_password_reset(self):
        email = self.rec_email.get().strip().lower()
        new_pw = self.rec_new_pw.get()
        if not email or not new_pw:
            messagebox.showwarning("Error", "Enter email and a new password.")
            return
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        if not user:
            messagebox.showerror("Error", "User not found.")
            return

        h1 = FirstQuestionHandler()
        h2 = SecondQuestionHandler()
        h3 = ThirdQuestionHandler()
        h1.set_next(h2).set_next(h3)

        ok, msg = h1.handle(dict(user), [e.get() for e in self.rec_answers])
        if not ok:
            messagebox.showerror("Failed", msg)
            return

        cur.execute(
            "UPDATE users SET password_hash = ? WHERE user_id = ?",
            (DatabaseManager.hash_password(new_pw), user["user_id"]),
        )
        self.db.conn.commit()
        messagebox.showinfo("Success", msg)


class MainDashboard(ttk.Frame):
    # Main tabs for DriveShare features
    def __init__(self, parent, db: DatabaseManager, session: SessionManager, mediator: UIMediator):
        super().__init__(parent)
        self.db, self.session, self.mediator = db, session, mediator
        self.mediator.register("dashboard", self)

        bar = ttk.Frame(self, style="Header.TFrame", padding=[14, 8])
        bar.pack(fill="x")
        self.banner = ttk.Label(bar, text="", style="Banner.TLabel")
        self.banner.pack(side="left")
        ttk.Button(bar, text="Logout", style="Secondary.TButton", command=lambda: self.mediator.notify("MainDashboard", "LOGOUT")).pack(side="right")
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=12)

        for attr, title, fn in [
            ("search_tab", "Search & Book", self.build_search_tab),
            ("owner_tab", "Car Management", self.build_owner_tab),
            ("bookings_tab", "Bookings & Payment", self.build_bookings_tab),
            ("msg_tab", "Messages", self.build_msg_tab),
            ("notif_tab", "Notifications", self.build_notif_tab),
        ]:
            frame = ttk.Frame(self.tabs, padding=10)
            setattr(self, attr, frame)
            self.tabs.add(frame, text=title)
            fn()

        self.refresh_all_tabs()

    def selected_id(self, tree: ttk.Treeview):
        sel = tree.selection()
        return tree.item(sel[0])["values"][0] if sel else None

    def notify_user(self, cur, user_id: int, text: str, stamp: str):
        cur.execute(
            "INSERT INTO notifications (user_id, message, created_at) VALUES (?, ?, ?)",
            (user_id, text, stamp),
        )

    def build_search_tab(self):
        top = ttk.Frame(self.search_tab, style="Card.TFrame", padding=10)
        top.pack(fill="x", pady=(0, 8))

        for lbl, attr, w in [("Location", "s_loc", 14), ("Date (YYYY-MM-DD)", "s_date", 12), ("Max Mileage", "s_miles", 10)]:
            ttk.Label(top, text=lbl, style="Field.TLabel").pack(side="left", padx=(0, 4))
            e = ttk.Entry(top, width=w)
            e.pack(side="left", padx=(0, 8))
            setattr(self, attr, e)

        ttk.Button(top, text="Search", style="Primary.TButton", command=self.load_cars_table).pack(side="left", padx=4)
        ttk.Button(top, text="Clear", style="Secondary.TButton", command=self.clear_filters).pack(side="left")

        cols = ("ID", "Model", "Year", "Mileage", "Location", "Price/Day", "Available Dates", "Available")
        self.cars_tree = ttk.Treeview(self.search_tab, columns=cols, show="headings", height=8)
        for c in cols:
            self.cars_tree.heading(c, text=c)
            self.cars_tree.column(c, width=105 if c != "ID" else 40)
        self.cars_tree.pack(fill="both", expand=True, pady=(0, 8))

        bot = ttk.Frame(self.search_tab, style="Card.TFrame", padding=10)
        bot.pack(fill="x")

        ttk.Label(bot, text="Start", style="Field.TLabel").pack(side="left", padx=(0, 4))
        self.b_start = ttk.Entry(bot, width=11)
        self.b_start.insert(0, "")
        self.b_start.pack(side="left", padx=(0, 6))

        ttk.Label(bot, text="End", style="Field.TLabel").pack(side="left", padx=(0, 4))
        self.b_end = ttk.Entry(bot, width=11)
        self.b_end.insert(0, "")
        self.b_end.pack(side="left", padx=(0, 6))

        ttk.Button(bot, text="Book Car", style="Primary.TButton", command=self.handle_book_car).pack(side="left", padx=(0, 12))

        ttk.Label(bot, text="Watch Max $", style="Field.TLabel").pack(side="left", padx=(0, 4))
        self.w_price = ttk.Entry(bot, width=7)
        self.w_price.insert(0, "")
        self.w_price.pack(side="left", padx=(0, 4))
        ttk.Button(bot, text="Watch Car", style="Secondary.TButton", command=self.handle_watch_car).pack(side="left", padx=4)
        ttk.Button(bot, text="Message Owner", style="Secondary.TButton", command=self.handle_message_owner).pack(side="left", padx=4)

    def clear_filters(self):
        for e in (self.s_loc, self.s_date, self.s_miles):
            e.delete(0, tk.END)
        self.load_cars_table()

    def load_cars_table(self):
        self.cars_tree.delete(*self.cars_tree.get_children())
        clauses, params = ["1=1"], []

        if self.s_loc.get().strip():
            clauses.append("LOWER(pickup_location) LIKE ?")
            params.append(f"%{self.s_loc.get().strip().lower()}%")
        if self.s_date.get().strip():
            d = self.s_date.get().strip()
            clauses.append("avail_start <= ? AND avail_end >= ?")
            params.extend([d, d])
        if self.s_miles.get().strip():
            try:
                max_miles = int(self.s_miles.get().strip())
                clauses.append("mileage <= ?")
                params.append(max_miles)
            except ValueError:
                messagebox.showerror("Error", "Max Mileage must be a whole number.")
                return

        cur = self.db.conn.cursor()
        cur.execute(f"SELECT * FROM cars WHERE {' AND '.join(clauses)}", params)
        for car in cur.fetchall():
            self.cars_tree.insert(
                "",
                tk.END,
                values=(
                    car["car_id"],
                    car["model"],
                    car["year"],
                    car["mileage"],
                    car["pickup_location"],
                    f"${car['daily_price']:.2f}",
                    f"{car['avail_start']} to {car['avail_end']}",
                    "Yes" if car["is_available"] else "No",
                ),
            )

    def handle_book_car(self):
        car_id = self.selected_id(self.cars_tree)
        if car_id is None:
            return
        start_s = self.b_start.get().strip()
        end_s = self.b_end.get().strip()
        try:
            d1 = datetime.strptime(start_s, "%Y-%m-%d")
            d2 = datetime.strptime(end_s, "%Y-%m-%d")
            if d2 < d1:
                raise ValueError("End date must be on or after start date.")
        except ValueError as err:
            messagebox.showerror("Error", str(err))
            return

        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM cars WHERE car_id = ?", (car_id,))
        car = cur.fetchone()
        renter_id = self.session.current_user["user_id"]

        if not car["is_available"] or start_s < car["avail_start"] or end_s > car["avail_end"]:
            messagebox.showerror("Unavailable", "Car is not available for those dates.")
            return

        # Prevent overlapping bookings on the same car
        cur.execute(
            """
            SELECT COUNT(*) FROM bookings
            WHERE car_id = ? AND NOT (end_date < ? OR start_date > ?)
            """,
            (car_id, start_s, end_s),
        )
        if cur.fetchone()[0] > 0:
            messagebox.showerror("Conflict", "Overlapping booking exists for this car.")
            return

        days = (d2 - d1).days + 1
        total = round(days * car["daily_price"], 2)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")

        cur.execute(
            """
            INSERT INTO bookings (car_id, renter_id, start_date, end_date, total_amount)
            VALUES (?, ?, ?, ?, ?)
            """,
            (car_id, renter_id, start_s, end_s, total),
        )
        self.notify_user(cur, car["owner_id"], f"Booking for {car['model']} ({start_s} to {end_s}).", stamp)
        self.notify_user(cur, renter_id, f"Reserved {car['model']} ({start_s} to {end_s}) for ${total:.2f}.", stamp)
        self.db.conn.commit()
        messagebox.showinfo("Booked", f"Reserved for ${total:.2f}.")
        self.mediator.notify("MainDashboard", "BOOKING_CREATED")

    def handle_watch_car(self):
        car_id = self.selected_id(self.cars_tree)
        if car_id is None:
            return
        try:
            max_p = float(self.w_price.get().strip())
        except ValueError:
            return
        cur = self.db.conn.cursor()
        cur.execute(
            "INSERT INTO watches (car_id, renter_id, max_price, notify_on_available) VALUES (?, ?, ?, 1)",
            (car_id, self.session.current_user["user_id"], max_p),
        )
        self.db.conn.commit()
        messagebox.showinfo("Watching", f"Watching Car #{car_id} up to ${max_p:.2f}/day.")

    def handle_message_owner(self):
        car_id = self.selected_id(self.cars_tree)
        if car_id is None:
            return
        cur = self.db.conn.cursor()
        cur.execute("SELECT owner_id FROM cars WHERE car_id = ?", (car_id,))
        row = cur.fetchone()
        if row:
            self.mediator.notify("MainDashboard", "OPEN_CHAT_WITH_OWNER", row["owner_id"])

    def build_owner_tab(self):
        form = ttk.Frame(self.owner_tab, style="Card.TFrame", padding=10)
        form.pack(fill="x", pady=(0, 8))

        fields = [
            ("Model", "c_model", 14),
            ("Year", "c_year", 7),
            ("Mileage", "c_miles", 8),
            ("Pickup Location", "c_loc", 13),
            ("Rental Price/Day", "c_price", 9),
            ("Start (YYYY-MM-DD)", "c_start", 11),
            ("End (YYYY-MM-DD)", "c_end", 11),
        ]
        for idx, (lbl, attr, w) in enumerate(fields):
            r, c = divmod(idx, 4)
            ttk.Label(form, text=lbl, style="Field.TLabel").grid(row=r * 2, column=c, sticky="w", padx=(0, 6))
            e = ttk.Entry(form, width=w)
            e.grid(row=r * 2 + 1, column=c, sticky="we", padx=(0, 6), pady=(2, 5))
            setattr(self, attr, e)

        ttk.Button(form, text="List Car", style="Primary.TButton", command=self.handle_add_car).grid(
            row=3, column=3, sticky="we", padx=(0, 6), pady=(2, 5)
        )

        cols = ("ID", "Model", "Year", "Mileage", "Location", "Price/Day", "Start", "End", "Available")
        self.owner_tree = ttk.Treeview(self.owner_tab, columns=cols, show="headings", height=7)
        for c in cols:
            self.owner_tree.heading(c, text=c)
            self.owner_tree.column(c, width=95 if c != "ID" else 40)
        self.owner_tree.pack(fill="both", expand=True, pady=(0, 8))

        upd = ttk.Frame(self.owner_tab, style="Card.TFrame", padding=10)
        upd.pack(fill="x")
        ttk.Label(upd, text="New Price", style="Field.TLabel").pack(side="left", padx=(0, 4))
        self.u_price = ttk.Entry(upd, width=9)
        self.u_price.pack(side="left", padx=(0, 8))
        self.u_avail = tk.IntVar(value=1)
        ttk.Checkbutton(upd, text="Available", variable=self.u_avail).pack(side="left", padx=(0, 10))
        ttk.Button(upd, text="Update Listing", style="Primary.TButton", command=self.handle_update_car).pack(side="left")

    def handle_add_car(self):
        try:
            listing = (
                ListingBuilder()
                .set_owner(self.session.current_user["user_id"])
                .set_vehicle_info(self.c_model.get(), int(self.c_year.get()), int(self.c_miles.get()))
                .set_rental_terms(self.c_loc.get(), float(self.c_price.get()), self.c_start.get(), self.c_end.get())
                .build()
            )
        except Exception as err:
            messagebox.showerror("Error", str(err))
            return

        cur = self.db.conn.cursor()
        cur.execute(
            """
            INSERT INTO cars (owner_id, model, year, mileage, pickup_location,
                              daily_price, avail_start, avail_end, is_available)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                listing.owner_id,
                listing.model,
                listing.year,
                listing.mileage,
                listing.pickup_location,
                listing.daily_price,
                listing.avail_start,
                listing.avail_end,
            ),
        )
        self.db.conn.commit()
        self.mediator.notify("MainDashboard", "CAR_UPDATED")

    def load_owner_cars(self):
        self.owner_tree.delete(*self.owner_tree.get_children())
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM cars WHERE owner_id = ?", (self.session.current_user["user_id"],))
        for car in cur.fetchall():
            self.owner_tree.insert(
                "",
                tk.END,
                values=(
                    car["car_id"],
                    car["model"],
                    car["year"],
                    car["mileage"],
                    car["pickup_location"],
                    f"${car['daily_price']:.2f}",
                    car["avail_start"],
                    car["avail_end"],
                    "Yes" if car["is_available"] else "No",
                ),
            )

    def handle_update_car(self):
        car_id = self.selected_id(self.owner_tree)
        if car_id is None:
            return
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM cars WHERE car_id = ?", (car_id,))
        car = cur.fetchone()
        new_price = float(self.u_price.get()) if self.u_price.get().strip() else car["daily_price"]
        new_avail = self.u_avail.get()
        cur.execute("UPDATE cars SET daily_price = ?, is_available = ? WHERE car_id = ?", (new_price, new_avail, car_id))
        self.db.conn.commit()

        CarSubject(self.db, car_id).notify("Listing updated")
        self.mediator.notify("MainDashboard", "CAR_UPDATED")

    def build_bookings_tab(self):
        cols = ("Booking ID", "Car", "Start", "End", "Total Amount")
        self.bookings_tree = ttk.Treeview(self.bookings_tab, columns=cols, show="headings", height=8)
        for c in cols:
            self.bookings_tree.heading(c, text=c)
        self.bookings_tree.pack(fill="both", expand=True, pady=(0, 8))

        pay_bar = ttk.Frame(self.bookings_tab, style="Card.TFrame", padding=10)
        pay_bar.pack(fill="x")
        ttk.Label(pay_bar, text="Amount", style="Field.TLabel").pack(side="left", padx=(0, 6))
        self.pay_amt = ttk.Entry(pay_bar, width=10)
        self.pay_amt.pack(side="left", padx=(0, 8))
        ttk.Button(pay_bar, text="Pay", style="Primary.TButton", command=self.handle_payment).pack(side="left")

    def load_bookings_table(self):
        self.bookings_tree.delete(*self.bookings_tree.get_children())
        uid = self.session.current_user["user_id"]
        cur = self.db.conn.cursor()
        cur.execute(
            """
            SELECT b.*, c.model
            FROM bookings b
            JOIN cars c ON b.car_id = c.car_id
            WHERE b.renter_id = ? OR c.owner_id = ?
            """,
            (uid, uid),
        )
        for b in cur.fetchall():
            self.bookings_tree.insert("", tk.END, values=(b["booking_id"], b["model"], b["start_date"], b["end_date"], f"${b['total_amount']:.2f}"))

    def handle_payment(self):
        booking_id = self.selected_id(self.bookings_tree)
        if booking_id is None:
            return
        try:
            amt = float(self.pay_amt.get().strip())
        except ValueError:
            return
        ok, msg = PaymentServiceProxy(self.db, self.session).process_payment(booking_id, self.session.current_user["user_id"], amt)
        messagebox.showinfo("Payment", msg)
        if ok:
            self.mediator.notify("MainDashboard", "PAYMENT_COMPLETED")

    def build_msg_tab(self):
        card = ttk.Frame(self.msg_tab, style="Card.TFrame", padding=10)
        card.pack(fill="both", expand=True)

        top = ttk.Frame(card, style="Card.TFrame")
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="To:", style="Field.TLabel").pack(side="left", padx=(0, 6))
        self.msg_to = ttk.Combobox(top, state="readonly", width=30)
        self.msg_to.pack(side="left")

        self.chat_box = tk.Text(card, height=10, state="disabled", bg="#f8fafc", relief="flat", padx=8, pady=8)
        self.chat_box.pack(fill="both", expand=True, pady=(0, 8))

        bot = ttk.Frame(card, style="Card.TFrame")
        bot.pack(fill="x")
        self.msg_entry = ttk.Entry(bot)
        self.msg_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ttk.Button(bot, text="Send", style="Primary.TButton", command=self.handle_send_message).pack(side="right")

    def load_messages(self):
        uid = self.session.current_user["user_id"]
        cur = self.db.conn.cursor()
        prev_choice = self.msg_to.get()
        cur.execute("SELECT user_id, email FROM users WHERE user_id != ?", (uid,))
        self.user_map = {r["email"]: r["user_id"] for r in cur.fetchall()}
        self.msg_to["values"] = list(self.user_map.keys())
        if prev_choice in self.user_map:
            self.msg_to.set(prev_choice)
        elif self.user_map and not self.msg_to.get():
            self.msg_to.current(0)

        cur.execute(
            """
            SELECT m.*, s.email AS sender_email, r.email AS receiver_email
            FROM messages m
            JOIN users s ON m.sender_id = s.user_id
            JOIN users r ON m.receiver_id = r.user_id
            WHERE m.sender_id = ? OR m.receiver_id = ?
            ORDER BY m.message_id ASC
            """,
            (uid, uid),
        )
        self.chat_box.config(state="normal")
        self.chat_box.delete("1.0", tk.END)
        for m in cur.fetchall():
            self.chat_box.insert(tk.END, f"[{m['timestamp']}] {m['sender_email']} -> {m['receiver_email']}: {m['content']}\n")
        self.chat_box.config(state="disabled")

    def jump_to_messages(self, user_id: int):
        self.tabs.select(self.msg_tab)
        for email, uid in self.user_map.items():
            if uid == user_id:
                self.msg_to.set(email)
                break

    def handle_send_message(self):
        target = self.msg_to.get()
        text = self.msg_entry.get().strip()
        if not target or not text:
            return
        recv_id = self.user_map[target]
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        cur = self.db.conn.cursor()
        cur.execute(
            "INSERT INTO messages (sender_id, receiver_id, content, timestamp) VALUES (?, ?, ?, ?)",
            (self.session.current_user["user_id"], recv_id, text, stamp),
        )
        self.notify_user(cur, recv_id, f"Message from {self.session.current_user['email']}: {text}", stamp)
        self.db.conn.commit()
        self.msg_entry.delete(0, tk.END)
        self.mediator.notify("MainDashboard", "MESSAGE_SENT")

    def build_notif_tab(self):
        self.notif_box = tk.Listbox(self.notif_tab, bg="#ffffff", relief="flat", highlightthickness=0)
        self.notif_box.pack(fill="both", expand=True)

    def load_notifications(self):
        self.notif_box.delete(0, tk.END)
        cur = self.db.conn.cursor()
        cur.execute(
            "SELECT * FROM notifications WHERE user_id = ? ORDER BY notif_id DESC",
            (self.session.current_user["user_id"],),
        )
        for n in cur.fetchall():
            self.notif_box.insert(tk.END, f"[{n['created_at']}] {n['message']}")

    def refresh_all_tabs(self):
        self.session.refresh_user(self.db)
        u = self.session.current_user
        self.banner.config(text=f"{u['email']}  |  Balance: ${u['balance']:.2f}")
        self.load_cars_table()
        self.load_owner_cars()
        self.load_bookings_table()
        self.load_messages()
        self.load_notifications()