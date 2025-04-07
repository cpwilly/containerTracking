import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.clock import Clock
import paho.mqtt.client as mqtt

# MQTT settings for local broker
BROKER = "localhost"
PORT = 1883
TOPIC = "container_tracking"

class MqttClient:
    def __init__(self, app):
        self.client = mqtt.Client()
        self.client.on_message = self.on_message
        self.app = app
        self.client.connect(BROKER, PORT, 60)
        self.client.subscribe(TOPIC)
        self.client.loop_start()

    def on_message(self, client, userdata, msg):
        instruction = msg.payload.decode('utf-8')
        # Schedule the UI update to be run in the main thread
        Clock.schedule_once(lambda dt: self.app.display_instruction(instruction))

    def start(self):
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()

class MqttApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Welcome screen setup
        self.welcome_label = Label(text="Container Tracking", font_size=30, halign='center', color=(0, 0, 1, 1))
        self.layout.add_widget(self.welcome_label)

        # Instructions section
        self.instruction_label = Label(text="Choose a Mode", font_size=24, size_hint_y=None, height=40)
        self.layout.add_widget(self.instruction_label)

        # Action Button
        self.action_button = Button(text="No action", size_hint_y=None, height=50, background_color=(0.2, 0.6, 0.2, 1))
        self.layout.add_widget(self.action_button)

        # Placeholder for success/error feedback
        self.feedback_label = Label(text="", font_size=20, size_hint_y=None, height=40)
        self.layout.add_widget(self.feedback_label)

        return self.layout

    def display_instruction(self, instruction):
        """Update the UI based on the received MQTT message"""
        if instruction == "return":
            self.update_ui("Scan Container", "Return", "Scan the container barcode.")
        elif instruction == "checkout":
            self.update_ui("Scan Container", "Checkout", "Scan the container barcode.")
        elif instruction == "checkout:badge":
                self.update_ui("Scan Badge", "Checkout", "Scan User Badge")
        elif "Success" in instruction:
            self.update_ui(instruction, "Success", "✅", success=True)
            # Schedule to reset UI after 1 second
            Clock.schedule_once(lambda dt: self.reset_ui(), 2)
        elif "Invalid" in instruction:
            self.update_ui(instruction, "Error", "❌ There was an error!", success=False)
            # Schedule to reset UI after 1 second
            Clock.schedule_once(lambda dt: self.reset_ui(), 2)
        else:
            self.update_ui("Choose a Mode", "No action", "")

    def update_ui(self, message, button_text, feedback_message, success=None):
        """Update UI elements based on instruction"""
        # Update the instruction label
        self.instruction_label.text = message
        
        # Update the action button text and color based on success or error
        self.action_button.text = button_text
        if success is None:
            self.action_button.background_color = (0.2, 0.6, 0.2, 1)  # Default color (green)
        elif success:
            self.action_button.background_color = (0.2, 0.8, 0.2, 1)  # Success color (light green)
        else:
            self.action_button.background_color = (0.8, 0.2, 0.2, 1)  # Error color (red)

        # Display feedback message for success or error
        self.feedback_label.text = feedback_message
        
        # Show the action button's corresponding functionality (like scanning)
        self.action_button.bind(on_press=self.show_scanner_popup)

    def reset_ui(self):
        """Reset the UI to the default state after success or error"""
        self.update_ui("Waiting for instructions...", "No action", "")

    def show_scanner_popup(self, instance):
        """Show a popup for scanning when the button is pressed"""
        popup_content = BoxLayout(orientation='vertical', padding=20)
        popup_label = Label(text="Scan the container barcode")
        popup_content.add_widget(popup_label)

        # Close button for the popup
        close_button = Button(text="Close", size_hint=(1, 0.25))
        popup_content.add_widget(close_button)

        popup = Popup(title="Scanner", content=popup_content, size_hint=(None, None), size=(400, 400))
        close_button.bind(on_press=popup.dismiss)

        popup.open()

    def on_stop(self):
        """Stop MQTT client when the app is closed"""
        self.mqtt_client.stop()

    def on_start(self):
        """Start MQTT client when the app starts"""
        self.mqtt_client = MqttClient(self)
        self.mqtt_client.start()

if __name__ == '__main__':
    MqttApp().run()
