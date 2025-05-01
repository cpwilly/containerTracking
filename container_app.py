import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.clock import Clock
import paho.mqtt.client as mqtt
from kivy.uix.textinput import TextInput
import socket
import fcntl
import struct


# MQTT settings for local broker
BROKER = "localhost"
PORT = 1883
TOPIC = "container_tracking"

def get_ip_address(ifname: str) -> str:
    """Get the IP address associated with the given network interface (Linux only)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915, 
            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
        )[20:24])
    except Exception:
        return 'IP not found'

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
        Clock.schedule_once(lambda dt: self.app.display_instruction(instruction))

    def start(self):
        self.client.loop_start()

    def stop(self):
        self.client.loop_stop()

class MqttApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        
        # Welcome screen 
        self.welcome_label = Label(text="Container Tracking", font_size=25, halign='center', color=(0, 0, 1, 1))
        self.layout.add_widget(self.welcome_label)

        # Instructions section
        self.instruction_label = Label(text="Choose a Mode", font_size=24, size_hint_y=None, height=40)
        self.layout.add_widget(self.instruction_label)

        # Action Button
        self.checkout_button = Button(text="Checkout", size_hint_y=None, height=50, background_color=(0.2, 0.6, 0.2, 1))
        self.layout.add_widget(self.checkout_button)
        self.checkout_button.bind(on_press=self.checkout_mode)
        
        # Action Button
        self.return_button = Button(text="Return", size_hint_y=None, height=50, background_color=(0.1, 0.4, 0.6, 1))
        self.layout.add_widget(self.return_button)
        self.return_button.bind(on_press=self.return_mode)

        # Placeholder for success/error feedback if we need it
        self.feedback_label = Label(text="", font_size=20, size_hint_y=None, height=40)
        self.layout.add_widget(self.feedback_label)
        
        # Show IP address 
        ip_address = get_ip_address("wlan0")
        self.ip_label = Label(
            text=f"Device IP: {ip_address}",
            font_size=16,
            size_hint_y=None,
            height=30,
            halign="center",
            valign="middle",
            color=(0.5, 0.5, 0.5, 1)
        )
        self.layout.add_widget(self.ip_label)


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
            self.update_ui(instruction, "Success", "", success=True)
            # one second reset
            Clock.schedule_once(lambda dt: self.reset_ui(), 2)
        elif "Error" in instruction:
            self.update_ui(instruction, "Error", "There was an error!", success=False)
            # one second reset
            Clock.schedule_once(lambda dt: self.reset_ui(), 2)
        else:
            self.update_ui("Choose a Mode", "No action", "")

    def update_ui(self, message, button_text, feedback_message, success=None):
        """Update UI elements based on instruction"""
        self.instruction_label.text = message
        
        if success is None:
            pass 
        elif success:
            self.show_feedback_popup(success=True, message=message)
        else:
            self.show_feedback_popup(success=False, message=message)
        self.feedback_label.text = feedback_message

    def show_feedback_popup(self, success=True, message="Success"):
        """Show a fullscreen popup with success or error message that auto-dismisses after 1 second."""
        popup_content = BoxLayout(orientation='vertical', padding=0, spacing=0)
        
        feedback_label = Label(text=message, font_size=30, color=(1, 1, 1, 1), size_hint=(1, 1))
        popup_content.add_widget(feedback_label)
        
        feedback_popup = Popup(
            title="",  
            content=popup_content,
            size_hint=(1, 1),  
            auto_dismiss=False 
        )
        
        # Set background color 
        if success:
            feedback_popup.background_color = (0.2, 0.8, 0.2, 1)  # Green 
        else:
            feedback_popup.background_color = (0.8, 0.2, 0.2, 1)  # Red
        
        # Show the popup
        feedback_popup.open()
        
        # Dismiss the popup after 1 second
        Clock.schedule_once(lambda dt: feedback_popup.dismiss(), 1)

    def reset_ui(self):
        """Reset the UI to the default state after success or error"""
        self.update_ui("Select Mode", "No action", "")

        
    def checkout_mode(self, instance):
        """Show a popup for scanning when the button is pressed"""
        # Create a popup with a TextInput
        popup_content = BoxLayout(orientation='vertical', padding=20)
        
        popup_title = Label(text="Checkout", font_size=40, size_hint_y=None, height=60)
        popup_content.add_widget(popup_title)

        popup_header = Label(text="Scan Container", font_size=35, size_hint_y=None, height=50)
        popup_content.add_widget(popup_header)

        # make input area invisable
        input_text = TextInput(hint_text="Type here", multiline=False, opacity=0, height=0)
        popup_content.add_widget(input_text)
        badge_text = TextInput(hint_text="Type here", multiline=False, opacity=0, height=0)
        popup_content.add_widget(badge_text)

        # hidden button
        submit_button = Button(opacity=0, text="", size_hint=(1, 0.25))
        popup_content.add_widget(submit_button)

        popup = Popup(title="Input", content=popup_content, size_hint=(None, None), size=(400, 400))

        # When the submit button is pressed, publish the input as MQTT message
        def on_submit(instance):
            input_value = input_text.text.strip()
            badge_value = badge_text.text.strip()
            if input_value:
                self.mqtt_client.client.publish(TOPIC, f"control:checkout:{input_value}:{badge_value}")
            popup.dismiss()

        submit_button.bind(on_press=on_submit)

        def on_popup_open(popup_instance):
            input_text.focus = True  # Focus on the input box after opening the popup

        popup.bind(on_open=on_popup_open)

        def on_focus_change_input(instance, value):
            if not value:  # If the input box loses focus
                badge_text.focus = True
                popup_header.text = "Scan Badge"

        def on_focus_change_badge(instance, value):
            if not value:  # If the badge box loses focus
                on_submit(submit_button)  # Automatically call submit when focus is lost
                
        input_text.bind(focus=on_focus_change_input)
        badge_text.bind(focus=on_focus_change_badge)

        popup.open()

    #Return screen, same logic as checkout with only needing container
    def return_mode(self, instance):
            """Show a popup for scanning when the button is pressed"""

            popup_content = BoxLayout(orientation='vertical', padding=20)
            
            popup_title = Label(text="Return", font_size=40, size_hint_y=None, height=60)
            popup_content.add_widget(popup_title)

            popup_header = Label(text="Scan Container", font_size=30, size_hint_y=None, height=40)
            popup_content.add_widget(popup_header)

            input_text = TextInput(hint_text="Type here", multiline=False, opacity=0, height=0)
            popup_content.add_widget(input_text)

            submit_button = Button(opacity=0, text="", size_hint=(1, 0.25))
            popup_content.add_widget(submit_button)

            popup = Popup(title="Input", content=popup_content, size_hint=(None, None), size=(400, 400))

            def on_submit(instance):
                input_value = input_text.text.strip()
                if input_value:
                    self.mqtt_client.client.publish(TOPIC, f"control:return:{input_value}")
                popup.dismiss()

            submit_button.bind(on_press=on_submit)

            def on_popup_open(popup_instance):
                input_text.focus = True

            popup.bind(on_open=on_popup_open)

            def on_focus_change_input(instance, value):
                if not value:  
                    on_submit(submit_button) 

            input_text.bind(focus=on_focus_change_input)
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
