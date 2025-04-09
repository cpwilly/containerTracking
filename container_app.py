import kivy
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.popup import Popup
from kivy.clock import Clock
import paho.mqtt.client as mqtt
from kivy.uix.textinput import TextInput


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
            self.update_ui(instruction, "Success", "", success=True)
            # Schedule to reset UI after 1 second
            Clock.schedule_once(lambda dt: self.reset_ui(), 2)
        elif "Error" in instruction:
            self.update_ui(instruction, "Error", "There was an error!", success=False)
            # Schedule to reset UI after 1 second
            Clock.schedule_once(lambda dt: self.reset_ui(), 2)
        else:
            self.update_ui("Choose a Mode", "No action", "")

    def update_ui(self, message, button_text, feedback_message, success=None):
        """Update UI elements based on instruction"""
        # Update the instruction label
        self.instruction_label.text = message
        
        if success is None:
            pass  # Do nothing if success is None
        elif success:
            self.show_feedback_popup(success=True, message=message)
        else:
            self.show_feedback_popup(success=False, message=message)

        # Display feedback message for success or error
        self.feedback_label.text = feedback_message

    def show_feedback_popup(self, success=True, message="Success"):
        """Show a fullscreen popup with success or error message that auto-dismisses after 1 second."""
        # Create the content for the popup
        popup_content = BoxLayout(orientation='vertical', padding=0, spacing=0)
        
        # Create the label for the message
        feedback_label = Label(text=message, font_size=30, color=(1, 1, 1, 1), size_hint=(1, 1))
        popup_content.add_widget(feedback_label)
        
        # Create the popup
        feedback_popup = Popup(
            title="",  # No title needed
            content=popup_content,
            size_hint=(1, 1),  # Fullscreen
            auto_dismiss=False  # Prevent automatic dismissal
        )
        
        # Set background color based on success or error
        if success:
            feedback_popup.background_color = (0.2, 0.8, 0.2, 1)  # Green background for success
        else:
            feedback_popup.background_color = (0.8, 0.2, 0.2, 1)  # Red background for error
        
        # Show the popup
        feedback_popup.open()
        
        # Dismiss the popup after 1 second
        Clock.schedule_once(lambda dt: feedback_popup.dismiss(), 1)

    def reset_ui(self):
        """Reset the UI to the default state after success or error"""
        self.update_ui("Select Mode", "No action", "")

        
    def checkout_mode(self, instance):
        """Show a popup for scanning when the button is pressed"""
        # Create a popup with a TextInput to capture user input
        popup_content = BoxLayout(orientation='vertical', padding=20)
        
        # Add a large title label
        popup_title = Label(text="Checkout", font_size=40, size_hint_y=None, height=60)
        popup_content.add_widget(popup_title)

        # Add a smaller header with instructions
        popup_header = Label(text="Scan Container", font_size=20, size_hint_y=None, height=40)
        popup_content.add_widget(popup_header)

        # Create a TextInput widget (invisible)
        input_text = TextInput(hint_text="Type here", multiline=False, opacity=0, height=0)
        popup_content.add_widget(input_text)
        badge_text = TextInput(hint_text="Type here", multiline=False, opacity=0, height=0)
        popup_content.add_widget(badge_text)

        # Button to submit input (to simulate scan and submit)
        submit_button = Button(opacity=0, text="", size_hint=(1, 0.25))
        popup_content.add_widget(submit_button)

        # Create the popup
        popup = Popup(title="Input", content=popup_content, size_hint=(None, None), size=(400, 400))

        # When the submit button is pressed, publish the input as MQTT message
        def on_submit(instance):
            input_value = input_text.text.strip()
            badge_value = badge_text.text.strip()
            if input_value:
                # Publish the control input with the user input
                self.mqtt_client.client.publish(TOPIC, f"control:checkout:{input_value}:{badge_value}")
            popup.dismiss()

        submit_button.bind(on_press=on_submit)

        # Define the on_open event for the popup to focus on the TextInput after it opens
        def on_popup_open(popup_instance):
            input_text.focus = True  # Focus on the input box after opening the popup

        # Bind the on_open event to focus on the input box
        popup.bind(on_open=on_popup_open)

        # Bind to the focus property of the TextInput
        def on_focus_change_input(instance, value):
            if not value:  # If the input box loses focus
                badge_text.focus = True

        def on_focus_change_badge(instance, value):
            if not value:  # If the input box loses focus
                on_submit(submit_button)  # Automatically call submit when focus is lost
                
        input_text.bind(focus=on_focus_change_input)
        badge_text.bind(focus=on_focus_change_badge)

        # Open the popup
        popup.open()


    def return_mode(self, instance):
            """Show a popup for scanning when the button is pressed"""

            # Create a popup with a TextInput to capture user input
            popup_content = BoxLayout(orientation='vertical', padding=20)
            
            # Add a large title label
            popup_title = Label(text="Return", font_size=40, size_hint_y=None, height=60)
            popup_content.add_widget(popup_title)

            # Add a smaller header with instructions
            popup_header = Label(text="Scan Container", font_size=20, size_hint_y=None, height=40)
            popup_content.add_widget(popup_header)

            # Create a TextInput widget (invisible)
            input_text = TextInput(hint_text="Type here", multiline=False, opacity=0, height=0)
            popup_content.add_widget(input_text)

            # Button to submit input (to simulate scan and submit)
            submit_button = Button(opacity=0, text="", size_hint=(1, 0.25))
            popup_content.add_widget(submit_button)

            # Create the popup
            popup = Popup(title="Input", content=popup_content, size_hint=(None, None), size=(400, 400))

            # When the submit button is pressed, publish the input as MQTT message
            def on_submit(instance):
                input_value = input_text.text.strip()
                if input_value:
                    # Publish the control input with the user input
                    self.mqtt_client.client.publish(TOPIC, f"control:return:{input_value}")
                popup.dismiss()

            submit_button.bind(on_press=on_submit)

            # Define the on_open event for the popup to focus on the TextInput after it opens
            def on_popup_open(popup_instance):
                input_text.focus = True  # Focus on the input box after opening the popup

            # Bind the on_open event to focus on the input box
            popup.bind(on_open=on_popup_open)

            # Bind to the focus property of the TextInput
            def on_focus_change_input(instance, value):
                if not value:  # If the input box loses focus
                    on_submit(submit_button)  # Automatically call submit when focus is lost

                    
            input_text.bind(focus=on_focus_change_input)
            # Open the popup
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
