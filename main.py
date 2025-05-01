import sqlite3
import paho.mqtt.client as mqtt
from flask import Flask, render_template, request, redirect, url_for, jsonify
import threading


# MQTT settings for local broker
BROKER = "localhost"  
PORT = 1883 
TOPIC = "container_tracking"
FEED = "container_controls"

mqttMode = False

# MQTT client setup
mqtt_client = mqtt.Client()

def create_database():
    """Create the database and tables."""
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()

    # Containers
    cursor.execute('''CREATE TABLE IF NOT EXISTS containers (
                        id INTEGER PRIMARY KEY,
                        serial_number TEXT UNIQUE,
                        user_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users(id))''')

    # Users
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
    
    # Already exists
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
    
    # Already exists
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

    # Assign
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
    
    # Remove user association
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
    print(f"Publishing to MQTT: {instruction}")
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
    elif "control:checkout" in message:  
        # Split the message with :
        parts = message.split(":")
        
        # Ensure there are 4 parts ( control, checkout, container serial, badge ID)
        if len(parts) == 4:
            container_serial = parts[2]
            user_badgeID = parts[3]
            
            checkout_container(container_serial, user_badgeID)
        else:
            print("Error: Invalid message format. Expected format 'control:checkout:{container_serial}:{user_badgeID}'.")
    elif "control:return" in message:  # Check if message contains "control:checkout"
        # Split the message with :
        parts = message.split(":")
        
        # Ensure there are 3 parts ( control, checkout, container serial)
        if len(parts) == 3:
            container_serial = parts[2]
            
            return_container(container_serial)
        else:
            print("Error: Invalid message format. Expected format 'control:return:{container_serial}'.")

def run_flask():
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

def main():
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Connect to MQTT broker
    mqtt_client.on_message = on_message  
    mqtt_client.connect(BROKER, PORT, 60)
    mqtt_client.subscribe(TOPIC)        
    mqtt_client.loop_start() 

    create_database()  
    
    try:
        while True:
            pass
    except KeyboardInterrupt:
        print("Service interrupted. Shutting down.")

app = Flask(__name__)

@app.route('/', methods=['GET'])
def index():
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()

    cursor.execute("""
        SELECT users.id, users.name, users.badgeID, COUNT(containers.id) as container_count
        FROM users
        LEFT JOIN containers ON users.id = containers.user_id
        GROUP BY users.id
    """)
    users = cursor.fetchall()

    cursor.execute("""
        SELECT containers.id, containers.serial_number, users.name
        FROM containers
        LEFT JOIN users ON containers.user_id = users.id
    """)
    containers = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM containers WHERE user_id IS NOT NULL")
    checked_out = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM containers WHERE user_id IS NULL")
    available = cursor.fetchone()[0]

    conn.close()

    return render_template(
        'index.html',
        users=users,
        containers=containers,
        checked_out=checked_out,
        available=available
    )



@app.route('/add_user', methods=['POST'])
def add_user_route():
    name = request.form['name']
    badgeID = request.form['badgeID']
    add_user(name, badgeID)
    return redirect(url_for('index'))

@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/add_container', methods=['POST'])
def add_container_route():
    serial = request.form['serial_number']
    add_container(serial)
    return redirect(url_for('index'))

@app.route('/delete_container/<int:container_id>', methods=['POST'])
def delete_container(container_id):
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM containers WHERE id=?", (container_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/users', methods=['GET'])
def get_users_with_containers():
    conn = sqlite3.connect('container_tracking.db')
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, badgeID FROM users")
    users = cursor.fetchall()

    user_list = []
    for user in users:
        user_id, name, badgeID = user
        cursor.execute("SELECT serial_number FROM containers WHERE user_id=?", (user_id,))
        containers = [row[0] for row in cursor.fetchall()]
        user_list.append({
            'id': user_id, 
            'name': name,
            'badgeID': badgeID,
            'containers': containers
        })

    conn.close()
    return jsonify(user_list)

if __name__ == "__main__":
    main()
