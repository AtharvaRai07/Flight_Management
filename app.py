import pymysql
import hashlib
import random
from twilio.rest import Client
from translation import translations

# Database configuration
DB_HOST = 'localhost'
DB_USER = 'root'
DB_PASSWORD = 'toor'
DB_NAME = 'flight_management'

# Twilio configuration (Replace with your own Twilio SID, Auth Token, and Twilio phone number)
TWILIO_SID = ''
TWILIO_AUTH_TOKEN = '94edee1800d7a5f223282940021bd196'
TWILIO_PHONE_NUMBER = '+16193135432'

# Helper function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to send OTP via SMS using Twilio
def send_otp_mobile(phone_number, otp):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Your OTP for login is: {otp}",
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print("OTP sent successfully to your mobile.")
        return True
    except Exception as e:
        print(f"Error sending OTP: {e}")
        return False

# Function to create the Users table if it doesn't exist
def create_users_table():
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    try:
        with connection.cursor() as cursor:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS Users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(50) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                name VARCHAR(100),
                email VARCHAR(100),
                phone VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
            cursor.execute(create_table_query)
            connection.commit()
            print("Users table created successfully (if it didn't already exist).")
    except pymysql.MySQLError as e:
        print("Error while creating Users table:", e)
    finally:
        connection.close()

# Signup function to register new users
def signup(username, password, name, email, phone):
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    try:
        with connection.cursor() as cursor:
            hashed_password = hash_password(password)
            cursor.execute("INSERT INTO Users (username, password, name, email, phone) VALUES (%s, %s, %s, %s, %s)", 
                           (username, hashed_password, name, email, phone))
            connection.commit()
            print("Signup successful! You can now login.")
    except pymysql.MySQLError as e:
        print("Error during signup:", e)
    finally:
        connection.close()

# Login function with OTP verification
def login(username, password):
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    try:
        with connection.cursor() as cursor:
            hashed_password = hash_password(password)
            cursor.execute("SELECT user_id, phone FROM Users WHERE username = %s AND password = %s", 
                           (username, hashed_password))
            user = cursor.fetchone()
            if user:
                user_id, phone_number = user
                otp = random.randint(100000, 999999)
                if send_otp_mobile(phone_number, otp):
                    entered_otp = input("Enter the OTP sent to your mobile: ")
                    if str(otp) == entered_otp:
                        print("Login successful!")
                        return user_id
                    else:
                        print("Invalid OTP. Login failed.")
                        return None
                else:
                    print("Failed to send OTP. Please try again.")
                    return None
            else:
                print("Invalid username or password.")
                return None
    except pymysql.MySQLError as e:
        print("Error during login:", e)
    finally:
        connection.close()

# Fake money balance for the user (simulating a virtual wallet)
fake_money_balance = 2000.00

# Function to search available flights based on origin and destination
def search_flights(origin, destination):
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    available_flights = []
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT flight_number, airline, price 
                FROM flights 
                WHERE departure_city = %s AND arrival_city = %s
            """, (origin, destination))
            available_flights = cursor.fetchall()
    except pymysql.MySQLError as e:
        print("Error while fetching flights:", e)
    finally:
        connection.close()
    return available_flights
def view_bookings(user_id):
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    try:
        with connection.cursor() as cursor:
            query = """
                SELECT booking_id, flight_number, booking_date, price, food_choice, status
                FROM Bookings
                WHERE user_id = %s AND status = 'CONFIRMED'
            """
            cursor.execute(query, (user_id,))
            bookings = cursor.fetchall()
            return bookings
    except pymysql.MySQLError as e:
        print(f"Error fetching bookings: {e}")
        return

def cancel_booking(booking_id, user_id):
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    try:
        with connection.cursor() as cursor:
            # Check if booking exists and belongs to user
            cursor.execute("""
                SELECT price, status
                FROM Bookings
                WHERE booking_id = %s AND user_id = %s
            """, (booking_id, user_id))
            booking = cursor.fetchone()
            
            if not booking:
                print("Booking not found or unauthorized.")
                return False
                
            if booking[1] != 'CONFIRMED':
                print("Booking is already cancelled.")
                return False
            
            # Update booking status
            cursor.execute("""
                UPDATE Bookings
                SET status = 'CANCELLED'
                WHERE booking_id = %s
            """, (booking_id,))
            
            # Refund the amount
            global fake_money_balance
            fake_money_balance += float(booking[0])
            
            connection.commit()
            
            # Send cancellation confirmation
            cursor.execute("SELECT phone FROM Users WHERE user_id = %s", (user_id,))
            phone_number = cursor.fetchone()[0]
            send_cancellation_confirmation(phone_number, booking_id)
            
            print(f"Booking cancelled successfully. Refunded amount: ${booking[0]}")
            return True
    except pymysql.MySQLError as e:
        print(f"Error cancelling booking: {e}")
        return False
    finally:
        connection.close()

def send_cancellation_confirmation(phone_number, booking_id, flight_number):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Booking #{booking_id} {flight_number} has been cancelled. The refund will be processed shortly.",
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print("Cancellation confirmation sent successfully.")
        return True
    except Exception as e:
        print(f"Error sending cancellation confirmation: {e}")
        return False    
def send_booking_confirmation(phone_number, flight_number, airline):
    try:
        client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f"Booking Confirmed!\nFlight: {flight_number}\nAirline: {airline}\nThank you for booking with us!",
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        print("Booking confirmation sent successfully.")
        return True
    except Exception as e:
        print(f"Error sending booking confirmation: {e}")
        return False

# Function to book a flight by deducting from user's fake balance
def book_flight(flight, user_id, user_balance):
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    flight_price = float(flight[2])
    
    if user_balance >= flight_price:
        try:
            with connection.cursor() as cursor:
                # Select food option
                food_choice = select_food_option()
                if food_choice is None:
                    return user_balance  # Exit if no food option was selected
                
                # Record the booking with food choice
                insert_query = """
                    INSERT INTO Bookings (user_id, flight_number, price, food_choice)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(insert_query, (user_id, flight[0], flight_price, food_choice))
                connection.commit()
                
                print(f"Booking successful for {flight[0]} - {flight[1]} with food choice: {food_choice}")
                user_balance -= flight_price
                print(f"Remaining balance: ${user_balance:.2f}")
                return user_balance
        except pymysql.MySQLError as e:
            print(f"Error during booking: {e}")
            return user_balance
        finally:
            connection.close()
    else:
        print("Insufficient funds for booking.")
        return user_balance

def create_bookings_table():
    connection = pymysql.connect(host=DB_HOST, user=DB_USER, password=DB_PASSWORD, db=DB_NAME)
    try:
        with connection.cursor() as cursor:
            create_table_query = """
            CREATE TABLE IF NOT EXISTS Bookings (
                booking_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT,
                flight_number VARCHAR(20),
                booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                price DECIMAL(10,2),
                status VARCHAR(20) DEFAULT 'CONFIRMED',
                FOREIGN KEY (user_id) REFERENCES Users(user_id)
            );
            """
            cursor.execute(create_table_query)
            connection.commit()
            print("Bookings table created successfully.")
            
            # Check if the table was created
            cursor.execute("SHOW TABLES LIKE 'Bookings'")
            if cursor.fetchone():
                print("Bookings table exists.")
            else:
                print("Bookings table does not exist.")
    except pymysql.MySQLError as e:
        print("Error while creating Bookings table:", e)
    finally:
        connection.close()
def get_food_options():
    # Example food options
    food_options = [
        "Vegetarian Meal",
        "Chicken Meal",
        "Vegan Meal",
        "Gluten-Free Meal"
    ]
    return food_options

def select_food_option():
    food_options = get_food_options()
    print("\nAvailable Food Options:")
    for idx, option in enumerate(food_options, 1):
        print(f"{idx}. {option}")
    
    choice = int(input("Select a food option (1-5): "))
    if 1 <= choice <= len(food_options):
        return food_options[choice - 1]
    else:
        print("Invalid choice. No food option selected.")
        return None
# Main function to handle the booking process
def main():
    print("Welcome to the Flight Booking System!")
    origin = input("Enter your origin city: ")
    destination = input("Enter your destination city: ")
    available_flights = search_flights(origin, destination)

    if available_flights:
        print(f"\nAvailable flights from {origin} to {destination}:")
        for idx, flight in enumerate(available_flights, 1):
            print(f"{idx}. Flight {flight[0]} - {flight[1]} - ${flight[2]:.2f}")

        flight_choice = int(input("\nSelect a flight number to book: "))
        if 1 <= flight_choice <= len(available_flights):
            selected_flight = available_flights[flight_choice - 1]
            print(f"\nYou selected {selected_flight[0]} with {selected_flight[1]}")

            global fake_money_balance
            fake_money_balance = book_flight(selected_flight, fake_money_balance)
            if fake_money_balance != 2000.00:
                print("Thank you for booking with us!")
            else:
                print("Please try again with sufficient funds.")
        else:
            print("Invalid flight selection.")
    else:
        print("No flights available for the selected route.")

# Function to book a ticket
def book_ticket(user_id):
    try:
        print("Booking a ticket for user_id:", user_id)  # Debug print
        origin = input("Enter your origin city: ")
        destination = input("Enter your destination city: ")
        available_flights = search_flights(origin, destination)

        if available_flights:
            print(f"\nAvailable flights from {origin} to {destination}:")
            for idx, flight in enumerate(available_flights, 1):
                print(f"{idx}. Flight {flight[0]} - {flight[1]} - ${flight[2]:.2f}")

            flight_choice = int(input("\nSelect a flight number to book: "))
            if 1 <= flight_choice <= len(available_flights):
                selected_flight = available_flights[flight_choice - 1]
                print(f"\nYou selected {selected_flight[0]} with {selected_flight[1]}")

                global fake_money_balance
                fake_money_balance = book_flight(selected_flight, user_id, fake_money_balance)
                if fake_money_balance != 2000.00:
                    print("Thank you for booking with us!")
                else:
                    print("Please try again with sufficient funds.")
            else:
                print("Invalid flight selection.")
        else:
            print("No flights available for the selected route.")
    except Exception as e:
        print(f"Error during booking: {e}")

def money_add():
    global fake_money_balance
    print("Welcome to add money")
    amount = float(input("Enter the amount to add: "))
    fake_money_balance += amount
    print(f"Added ${amount:.2f} to your balance. Your new balance is ${fake_money_balance}")

# User interactive menu
def user_menu():
    # Language Selection
    print("Select Language:")
    print("1. English")
    print("2. Hindi")
    print("3. Chinese")
    print("4. Japanese")

    language_choice = input("Choose a language (1-4): ")

    if language_choice == '1':
        selected_language = 'en'
    elif language_choice == '2':
        selected_language = 'hi'
    elif language_choice == '3':
        selected_language = 'zh'
    elif language_choice == '4':
        selected_language = 'ja'
    else:
        print("Invalid choice. Defaulting to English.")
        selected_language = 'en'

    while True:
        print("\n--- Flight Management System ---")
        print(translations[selected_language]['signup'])
        print(translations[selected_language]['login'])
        print(translations[selected_language]['exit'])

        choice = input("Choose an option (1-3): ")

        if choice == '1':
            print("\n--- Sign Up ---")
            username = input(translations[selected_language]['enter_username'])
            password = input(translations[selected_language]['enter_password'])
            name = input(translations[selected_language]['enter_name'])
            email = input(translations[selected_language]['enter_email'])
            phone = input(translations[selected_language]['enter_phone'])
            signup(username, password, name, email, phone)
        
        elif choice == '2':
            print("\n--- Login ---")
            username = input(translations[selected_language]['enter_username'])
            password = input(translations[selected_language]['enter_password'])
            user_id = login(username, password)
            if user_id:
                print(translations[selected_language]['welcome_user'].format(username=username))
                
                # Display previous bookings after login
                bookings = view_bookings(user_id)
                if bookings:
                    print("\n" + translations[selected_language]['previous_bookings'])
                    for booking in bookings:
                        print(f"Booking ID: {booking[0]}, Flight: {booking[1]}, Date: {booking[2]}, Price: ${booking[3]}, Food Choice: {booking[4]}, Status: {booking[5]}")
                else:
                    print(translations[selected_language]['no_previous_bookings'])
                
                while True:
                    print("\n--- Flight Booking Menu ---")
                    print(translations[selected_language]['book_ticket'])
                    print(translations[selected_language]['view_bookings'])
                    print(translations[selected_language]['cancel_booking'])
                    print(translations[selected_language]['check_balance'])
                    print(translations[selected_language]['add_money'])
                    print(translations[selected_language]['logout'])

                    choice = input("Choose an option (1-6): ")

                    if choice == '1':
                        book_ticket(user_id)
                    elif choice == '2':
                        bookings = view_bookings(user_id)
                        if bookings:
                            print("\nYour Bookings:")
                            for booking in bookings:
                                print(f"Booking ID: {booking[0]} - Flight: {booking[1]} - Date: {booking[2]} - Price: ${booking[3]} - Food Choice: {booking[4]} - Status: {booking[5]}\n")
                        else:
                            print(translations[selected_language]['no_bookings_found'])
                    elif choice == '3':
                        booking_id = input(translations[selected_language]['enter_booking_id'])
                        cancel_booking(booking_id, user_id)
                    elif choice == '4':
                        print(translations[selected_language]['current_balance'].format(balance=fake_money_balance))
                    elif choice == '5':
                        money_add()
                    elif choice == '6':
                        print(translations[selected_language]['logging_out'])
                        break
                    else:
                        print(translations[selected_language]['invalid_choice'])

        elif choice == '3':
            print(translations[selected_language]['exiting'])
            break
        
        else:
            print(translations[selected_language]['invalid_choice'])

# Initial setup: Create the Users table
create_users_table()

# Start the user interactive menu
user_menu()