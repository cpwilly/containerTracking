import sqlite3
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

# SQLite database setup (same as before)
def create_database():
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS containers (
                        id INTEGER PRIMARY KEY,
                        serial_number TEXT UNIQUE,
                        user_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        name TEXT UNIQUE,
                        badgeID TEXT UNIQUE)''')
    conn.commit()
    conn.close()

# Database functions
def checkout_container(container_serial, user_badgeID):
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM containers WHERE serial_number=?", (container_serial,))
    container = cursor.fetchone()
    if not container:
        return f"Container {container_serial} does not exist."

    cursor.execute("SELECT * FROM users WHERE badgeID=?", (user_badgeID,))
    user = cursor.fetchone()
    if not user:
        return f"User with badge ID {user_badgeID} does not exist."

    cursor.execute("UPDATE containers SET user_id=? WHERE serial_number=?", (user[0], container_serial))
    conn.commit()
    conn.close()
    return f"Container {container_serial} checked out to {user[1]} (Badge ID: {user_badgeID})."

def return_container(container_serial):
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM containers WHERE serial_number=?", (container_serial,))
    container = cursor.fetchone()
    if not container:
        return f"Container {container_serial} does not exist."

    cursor.execute("UPDATE containers SET user_id=NULL WHERE serial_number=?", (container_serial,))
    conn.commit()
    conn.close()
    return f"Container {container_serial} returned and unassigned from user."

# Kivy UI
class ContainerTrackingApp(App):
    def build(self):
        self.root = BoxLayout(orientation='vertical', padding=20, spacing=10)

        self.label_title = Label(text="Container Tracker", font_size=32, size_hint_y=None, height=50, halign='center', valign='middle')
        self.root.add_widget(self.label_title)

        self.mode_label = Label(text="Select mode: Checkout or Return container", font_size=18, size_hint_y=None, height=50, halign='center', valign='middle')
        self.root.add_widget(self.mode_label)

        self.checkout_button = Button(text="Checkout Container", size_hint_y=None, height=50, on_press=self.checkout_mode)
        self.return_button = Button(text="Return Container", size_hint_y=None, height=50, on_press=self.return_mode)
        self.root.add_widget(self.checkout_button)
        self.root.add_widget(self.return_button)

        return self.root

    def checkout_mode(self, instance):
        self.clear_layout()

        self.container_label = Label(text="Enter container serial number", size_hint_y=None, height=50)
        self.user_label = Label(text="Enter user badge ID", size_hint_y=None, height=50)

        self.container_input = TextInput(hint_text="Container Serial", size_hint_y=None, height=40)
        self.user_input = TextInput(hint_text="User Badge ID", size_hint_y=None, height=40)

        self.submit_button = Button(text="Checkout Container", size_hint_y=None, height=50, on_press=self.checkout_container)

        self.root.add_widget(self.container_label)
        self.root.add_widget(self.container_input)
        self.root.add_widget(self.user_label)
        self.root.add_widget(self.user_input)
        self.root.add_widget(self.submit_button)

    def return_mode(self, instance):
        self.clear_layout()

        self.return_label = Label(text="Enter container serial number to return", size_hint_y=None, height=50)
        self.container_input = TextInput(hint_text="Container Serial", size_hint_y=None, height=40)

        self.return_button = Button(text="Return Container", size_hint_y=None, height=50, on_press=self.return_container)

        self.root.add_widget(self.return_label)
        self.root.add_widget(self.container_input)
        self.root.add_widget(self.return_button)

    def checkout_container(self, instance):
        container_serial = self.container_input.text.strip()
        user_badgeID = self.user_input.text.strip()
        
        result = checkout_container(container_serial, user_badgeID)

        popup = Popup(title="Result", content=Label(text=result), size_hint=(None, None), size=(400, 200))
        popup.open()

        self.clear_layout()

    def return_container(self, instance):
        container_serial = self.container_input.text.strip()

        result = return_container(container_serial)

        popup = Popup(title="Result", content=Label(text=result), size_hint=(None, None), size=(400, 200))
        popup.open()

        self.clear_layout()

    def clear_layout(self):
        # Clear the current layout (mode 2 or mode 3 UI) before switching modes
        for widget in self.root.children:
            self.root.remove_widget(widget)
        self.root.add_widget(self.label_title)
        self.root.add_widget(self.mode_label)
        self.root.add_widget(self.checkout_button)
        self.root.add_widget(self.return_button)

if __name__ == "__main__":
    create_database()  # Ensure the database exists
    app = ContainerTrackingApp()
    app.run()
