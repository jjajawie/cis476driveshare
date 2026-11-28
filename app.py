import tkinter as tk

from database import DatabaseManager
from backend import SessionManager, UIMediator
from ui import AuthFrame, MainDashboard, UI_Theme


# Top-level window that manages core services and switches between screens
class DriveShareApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("DriveShare")
        self.geometry("1280x960")
        UI_Theme(self)

        # Initialize database, session singleton, and UI mediator
        self.db = DatabaseManager()
        self.session = SessionManager()
        self.mediator = UIMediator()
        self.mediator.register("app", self)

        self.current_frame = None
        self.show_auth_screen()
        self.last_sig = None
        self.poll_db_changes()

    # Destroys the active frame cleanly before mounting the next one
    def swap_frame(self, next_frame):
        if self.current_frame is not None:
            self.current_frame.destroy()
        self.current_frame = next_frame
        self.current_frame.pack(fill="both", expand=True)

    def show_auth_screen(self):
        self.swap_frame(AuthFrame(self, self.db, self.session, self.mediator))

    def show_main_dashboard(self):
        self.swap_frame(MainDashboard(self, self.db, self.session, self.mediator))
    
    #Updates the app to reflect changes in the database
    def poll_db_changes(self):
        if isinstance(self.current_frame, MainDashboard) and self.session.is_authenticated:
            uid = self.session.current_user["user_id"]
            current_sig = self.db.get_sync_signature(uid)
            if current_sig != self.last_sig:
                self.last_sig = current_sig
                self.current_frame.refresh_all_tabs()
        #Updates every second
        self.after(100, self.poll_db_changes)
        
if __name__ == "__main__":
    DriveShareApp().mainloop()