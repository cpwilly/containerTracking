import queue
import time

# Simple code-to-name mapping
CODES = {
    "1234": "Carson",
    "5678": "Alex",
    "9999": "Jamie"
}

def check_user(code):
    """Check the user based on the entered code."""
    if code in CODES:
        name = CODES[code]
        return f"Your code is {code}, which means you are {name}!"
    else:
        return f"Code {code} is not recognized."

def run_terminal_input(input_queue):
    """Handle terminal input and put it in the queue."""
    print("Container Tracker")
    print("Enter your code")

    while True:
        code = input("Enter your code (or type 'exit' to quit): ").strip()
        
        if code.lower() == 'exit':
            print("Exiting the program...")
            break
        
        # Put the entered code in the input queue for the Kivy app to process
        input_queue.put(code)
        time.sleep(0.1)  # Small sleep to reduce CPU usage in CLI loop
