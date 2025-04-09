import sqlite3
import paho.mqtt.client as mqtt

# MQTT settings for local broker
BROKER = "localhost"  # Localhost for local MQTT broker
PORT = 1883  # Default MQTT port
TOPIC = "container_tracking"
FEED = "container_controls"

mqttMode = False

# MQTT client setup
mqtt_client = mqtt.Client()

def create_database():
    """Create the database and tables."""
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()

    # Create table for containers
    cursor.execute('''CREATE TABLE IF NOT EXISTS containers (
                        id INTEGER PRIMARY KEY,
                        serial_number TEXT UNIQUE,
                        user_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(id))''')

    # Create table for users (with name and badgeID)
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        name TEXT UNIQUE,
                        badgeID TEXT UNIQUE)''')

    conn.commit()
    conn.close()

def add_container(serial_number):
    """Add a new container to the database."""
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()
    
    # Check if container already exists
    cursor.execute("SELECT * FROM containers WHERE serial_number=?", (serial_number,))
    if cursor.fetchone():
        print(f"Container {serial_number} already exists.")
        publish_instruction(f"Error Container {serial_number} already exists")
    else:
        cursor.execute("INSERT INTO containers (serial_number) VALUES (?)", (serial_number,))
        conn.commit()
        print(f"Container {serial_number} added.")
        publish_instruction(f"Container {serial_number} added successfully ")
    
    conn.close()

def add_user(name, badgeID):
    """Add a new user to the database."""
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()
    
    # Check if user already exists
    cursor.execute("SELECT * FROM users WHERE name=? OR badgeID=?", (name, badgeID))
    if cursor.fetchone():
        print(f"User {name} with badge ID {badgeID} already exists.")
        publish_instruction(f"Error User {name} with badge ID {badgeID} already exists")
    else:
        cursor.execute("INSERT INTO users (name, badgeID) VALUES (?, ?)", (name, badgeID))
        conn.commit()
        print(f"User {name} with badge ID {badgeID} added.")
        publish_instruction(f"User {name} with Badge ID {badgeID} added successfully ")
    
    conn.close()

def checkout_container(container_serial, user_badgeID):
    """Checkout a container to a user."""
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()

    # Check if container exists
    cursor.execute("SELECT * FROM containers WHERE serial_number=?", (container_serial,))
    container = cursor.fetchone()
    if not container:
        print(f"Container {container_serial} does not exist.")
        publish_instruction(f"Error Container {container_serial} does not exist")
        return

    # Check if user exists by badgeID
    cursor.execute("SELECT * FROM users WHERE badgeID=?", (user_badgeID,))
    user = cursor.fetchone()
    if not user:
        print(f"User with badge ID {user_badgeID} does not exist.")
        publish_instruction(f"Error User with badge ID {user_badgeID} does not exist")
        return

    # Assign the container to the user (update user_id in containers table)
    cursor.execute("UPDATE containers SET user_id=? WHERE serial_number=?", (user[0], container_serial))
    conn.commit()
    print(f"Container {container_serial} checked out to {user[1]} (Badge ID: {user_badgeID}).")
    publish_instruction(f"Success {user[1]} ")
    
    conn.close()

def return_container(container_serial):
    """Return a container (remove its association with a user)."""
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()

    # Check if container exists
    cursor.execute("SELECT * FROM containers WHERE serial_number=?", (container_serial,))
    container = cursor.fetchone()
    if not container:
        print(f"Container {container_serial} does not exist.")
        publish_instruction(f"Error Container {container_serial} does not exist")
        return
    
    # Remove user association (set user_id to NULL)
    cursor.execute("UPDATE containers SET user_id=NULL WHERE serial_number=?", (container_serial,))
    conn.commit()
    print(f"Container {container_serial} returned and unassigned from user.")
    publish_instruction(f"Success ")
    
    conn.close()

def show_users_and_containers():
    """Show all users and containers in the database."""
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()

    # Display all users
    print("\n-- Users --")
    cursor.execute("SELECT id, name, badgeID FROM users")
    users = cursor.fetchall()
    if users:
        for user in users:
            print(f"ID: {user[0]}, Name: {user[1]}, Badge ID: {user[2]}")
    else:
        print("No users found.")

    # Display all containers
    print("\n-- Containers --")
    cursor.execute("SELECT id, serial_number, user_id FROM containers")
    containers = cursor.fetchall()
    if containers:
        for container in containers:
            user_assigned = "No user assigned"
            if container[2]:
                cursor.execute("SELECT name FROM users WHERE id=?", (container[2],))
                user_assigned = cursor.fetchone()[0]
            print(f"ID: {container[0]}, Serial Number: {container[1]}, Assigned to: {user_assigned}")
    else:
        print("No containers found.")

    conn.close()

def publish_instruction(instruction):
    """Publish an instruction to the MQTT broker."""
    print(f"Publishing to MQTT: {instruction}")  # Print the instruction being published for debug purposes
    mqtt_client.publish(TOPIC, instruction)

def display_menu():
    """Display the main menu for the app."""
    print("\n-- Container Tracking System --")
    print("1. Add Containers and Users")
    print("2. Checkout Container")
    print("3. Return Container")
    print("4. Show Users and Containers")
    print("5. Exit")
    choice = input("Choose an option: ")
    return choice

def handle_operation(operation):
    if operation == "checkout":
        publish_instruction(f"checkout")
        container_serial = input("Enter container serial number to checkout: ").strip()
        publish_instruction(f"checkout:badge")
        user_badgeID = input("Enter user badge ID: ").strip()
        checkout_container(container_serial, user_badgeID)
    elif operation == "return":
        publish_instruction(f"return")
        container_serial = input("Enter container serial number to return: ").strip()
        return_container(container_serial)
    mqttMode=False

def on_message(client, userdata, msg):
    message = msg.payload.decode().strip().lower()
    print(f"Received MQTT message: {message}")
    
    if message == "test":
        mqttMode = True
        handle_operation("checkout")
    elif "control:checkout" in message:  # Check if message contains "control:checkout"
        # Split the message by ":"
        parts = message.split(":")
        
        # Ensure there are 4 parts (including "control", "checkout", container serial, and badge ID)
        if len(parts) == 4:
            container_serial = parts[2]
            user_badgeID = parts[3]
            
            # Pass the parsed values to the checkout_container function
            checkout_container(container_serial, user_badgeID)
        else:
            print("Error: Invalid message format. Expected format 'control:checkout:{container_serial}:{user_badgeID}'.")
    elif "control:return" in message:  # Check if message contains "control:checkout"
        # Split the message by ":"
        parts = message.split(":")
        
        # Ensure there are 4 parts (including "control", "checkout", container serial, and badge ID)
        if len(parts) == 3:
            container_serial = parts[2]
            
            # Pass the parsed values to the checkout_container function
            return_container(container_serial)
        else:
            print("Error: Invalid message format. Expected format 'control:return:{container_serial}'.")

        

def main():
    # Connect to MQTT broker
    mqtt_client.on_message = on_message  # 👈 Add this line
    mqtt_client.connect(BROKER, PORT, 60)
    mqtt_client.subscribe(TOPIC)         # 👈 And this one
    mqtt_client.loop_start()  # Start MQTT loop

    create_database()  # Initialize the database
    
    while not mqttMode:
        choice = display_menu()

        if choice == '1':
            # Add containers and users
            mode = input("Would you like to add a container (C) or a user (U)? ").strip().upper()
            if mode == 'C':
                serial_number = input("Enter container serial number: ").strip()
                add_container(serial_number)
            elif mode == 'U':
                name = input("Enter user name: ").strip()
                badgeID = input("Enter user badge ID: ").strip()
                add_user(name, badgeID)
            else:
                print("Invalid choice. Please choose either 'C' for container or 'U' for user.")

        elif choice == '2':
            # Checkout container to a user
            handle_operation("checkout")

        elif choice == '3':
            # Return container
            handle_operation("return")

        elif choice == '4':
            # Show users and containers
            show_users_and_containers()

        elif choice == '5':
            # Exit the application
            print("Exiting the program...")
            publish_instruction("Exiting the system. Goodbye! 👋")
            break

        else:
            print("Invalid choice, please try again.")
            publish_instruction("Invalid choice. Please try again")


if __name__ == "__main__":
    main()
