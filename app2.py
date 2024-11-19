import pymysql
import hashlib
import random
import requests
from datetime import datetime
import logging
from typing import Optional, List, Tuple, Dict
from decimal import Decimal

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='flight_management.log'
)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'toor',
    'db': 'flight_management',
    'charset': 'utf8mb4'
}

# API Configuration
TEXTBELT_API_URL = "https://textbelt.com/text"
TEXTBELT_API_KEY = "c84fbd3e56a10951002f38269eed5f58fda0a153NWibMAnmeQYH9QomITNnvTERm"

class SMS_Service:
    @staticmethod
    def send_sms(phone_number: str, message: str) -> bool:
        try:
            payload = {
                'phone': phone_number,
                'message': message,
                'key': TEXTBELT_API_KEY
            }
            response = requests.post(TEXTBELT_API_URL, data=payload)
            response_data = response.json()
            
            if response_data.get('success', False):
                logging.info(f"SMS sent successfully to {phone_number}")
                return True
            else:
                logging.error(f"SMS sending failed: {response_data}")
                return False
        except Exception as e:
            logging.error(f"Error sending SMS: {e}")
            return False

    @classmethod
    def send_otp(cls, phone_number: str, otp: str) -> bool:
        message = f"Your OTP for login is: {otp}"
        return cls.send_sms(phone_number, message)

    @classmethod
    def send_booking_confirmation(cls, phone_number: str, booking_id: int, flight_number: str) -> bool:
        message = f"Opps Airways \n BOOKING CONFIRMATION: Your booking #{booking_id}, for Flight {flight_number} has been successfully made."
        return cls.send_sms(phone_number, message)

    @classmethod
    def send_cancellation_confirmation(cls, phone_number: str, booking_id: int, flight_number: str) -> bool:
        message = f"Oops Airways \n BOOKING CANCELLATION: Your booking #{booking_id},for Flight {flight_number} has been cancelled. \n The refund will be processed shortly."
        return cls.send_sms(phone_number, message)

class DatabaseManager:
    def __init__(self):
        self.config = DB_CONFIG

    def get_connection(self):
        try:
            return pymysql.connect(**self.config)
        except pymysql.Error as e:
            logging.error(f"Database connection error: {e}")
            raise

    def initialize_tables(self):
        self.create_users_table()
        self.create_flights_table()
        self.create_bookings_table()
        self.populate_sample_flights()

    def create_users_table(self):
        query = """
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
        self.execute_query(query)

    def create_flights_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS Flights (
            flight_id INT AUTO_INCREMENT PRIMARY KEY,
            flight_number VARCHAR(20) UNIQUE NOT NULL,
            airline VARCHAR(100),
            departure_city VARCHAR(100),
            arrival_city VARCHAR(100),
            price DECIMAL(10,2),
            available_seats INT DEFAULT 100
        );
        """
        self.execute_query(query)

    def create_bookings_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS Bookings (
            booking_id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            flight_number VARCHAR(20),
            booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            price DECIMAL(10,2),
            food_choice VARCHAR(50),
            status VARCHAR(20) DEFAULT 'CONFIRMED',
            FOREIGN KEY (user_id) REFERENCES Users(user_id)
        );
        """
        self.execute_query(query)

    def populate_sample_flights(self):
        query = """
        INSERT IGNORE INTO Flights (flight_number, airline, departure_city, arrival_city, price)
        VALUES 
            ('FL001', 'SkyWings', 'New York', 'London', 500.00),
            ('FL002', 'AirSpace', 'London', 'Paris', 200.00),
            ('FL003', 'CloudLines', 'Paris', 'Tokyo', 800.00),
            ('FL004', 'StarFlights', 'Tokyo', 'Sydney', 600.00);
        """
        self.execute_query(query)

    def execute_query(self, query: str, params: tuple = None) -> Optional[List]:
        with self.get_connection() as connection:
            with connection.cursor() as cursor:
                try:
                    cursor.execute(query, params or ())
                    connection.commit()
                    return cursor.fetchall()
                except pymysql.Error as e:
                    logging.error(f"Query execution error: {e}")
                    connection.rollback()
                    raise

class UserManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.sms = SMS_Service()
        self.user_balance = Decimal(2000.00)  

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash the user's password using SHA256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def signup(self, username: str, password: str, name: str, email: str, phone: str) -> bool:
        """Handle user signup."""
        try:
            query = """
            INSERT INTO Users (username, password, name, email, phone)
            VALUES (%s, %s, %s, %s, %s)
            """
            hashed_password = self.hash_password(password)
            self.db.execute_query(query, (username, hashed_password, name, email, phone))
            logging.info(f"User {username} registered successfully")
            return True
        except Exception as e:
            logging.error(f"Error during signup: {e}")
            return False

    def login(self, username: str, password: str) -> Optional[int]:
        """Handle user login."""
        try:
            query = "SELECT user_id, phone FROM Users WHERE username = %s AND password = %s"
            hashed_password = self.hash_password(password)
            result = self.db.execute_query(query, (username, hashed_password))
            
            if result:
                user_id, phone = result[0]
                otp = str(random.randint(100000, 999999))
                if self.sms.send_otp(phone, otp):
                    entered_otp = input("Enter the OTP sent to your mobile: ")
                    if otp == entered_otp:
                        logging.info(f"User {username} logged in successfully")
                        return user_id
            return None
        except Exception as e:
            logging.error(f"Error during login: {e}")
            return None

    def add_money(self, amount: float) -> bool:
        """Add money to the user's account."""
        try:
            self.user_balance += Decimal(amount)  
            logging.info(f"Added ${amount} to user balance. New balance: ${self.user_balance:.2f}")
            return True
        except Exception as e:
            logging.error(f"Error adding money to user balance: {e}")
            return False

    def get_user_balance(self) -> Decimal:
        """Return the current user balance."""
        return self.user_balance

    def deduct_balance(self, amount: float) -> bool:
        """Deduct amount from the user's balance."""
        try:
            amount = Decimal(amount) 
            if self.user_balance >= amount:
                self.user_balance -= amount
                logging.info(f"Deducted ${amount} from user balance. New balance: ${self.user_balance:.2f}")
                return True
            else:
                logging.warning(f"Insufficient balance to deduct ${amount}. Current balance: ${self.user_balance:.2f}")
                return False
        except Exception as e:
            logging.error(f"Error deducting from user balance: {e}")
            return False

class FlightManager:
    def __init__(self, db_manager: DatabaseManager, user_manager: UserManager):
        self.db = db_manager
        self.sms = SMS_Service()
        self.user_manager = user_manager

    def book_flight(self, flight_number: str, user_id: int) -> bool:
        connection = None
        try:       
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                connection.begin()

                cursor.execute("""
                    SELECT price, available_seats 
                    FROM Flights 
                    WHERE flight_number = %s
                    FOR UPDATE
                """, (flight_number,))
                
                flight_result = cursor.fetchone()
                if not flight_result:
                    print("Flight not found.")
                    return False

                price, available_seats = flight_result

                # Check seats availability
                if available_seats <= 0:
                    print("Sorry, no available seats on this flight.")
                    return False

                # Check and deduct user balance
                if not self.user_manager.deduct_balance(float(price)):
                    print("Insufficient funds")
                    return False

                # Get food choice
                food_choice = self.select_food_option()

                # Create booking
                cursor.execute("""
                    INSERT INTO Bookings (user_id, flight_number, price, food_choice)
                    VALUES (%s, %s, %s, %s)
                """, (user_id, flight_number, price, food_choice))

                # Get booking ID
                booking_id = cursor.lastrowid

                # Update available seats
                cursor.execute("""
                    UPDATE Flights 
                    SET available_seats = available_seats - 1 
                    WHERE flight_number = %s
                """, (flight_number,))

                # Get user phone number
                cursor.execute("""
                    SELECT phone 
                    FROM Users 
                    WHERE user_id = %s
                """, (user_id,))
                
                user_result = cursor.fetchone()
                if user_result:
                    phone = user_result[0]
                    # Send booking confirmation SMS
                    self.sms.send_booking_confirmation(phone, booking_id, flight_number)

                # Commit the transaction
                connection.commit()
                print(f"Booking successful! Booking ID: {booking_id}")
                return True

        except Exception as e:
            logging.error(f"Error in book_flight: {e}")
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            return False
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def cancel_booking(self, booking_id: int, user_id: int) -> bool:
        connection = None
        try:
            # Begin transaction for booking cancellation
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                connection.begin()  # Start transaction

                # Fetch booking details (price, flight number, user phone)
                query = """
                SELECT price, status, flight_number, (SELECT phone FROM Users WHERE user_id = %s)
                FROM Bookings
                WHERE booking_id = %s AND user_id = %s
                """
                cursor.execute(query, (user_id, booking_id, user_id))
                result = cursor.fetchone()

                if not result or result[1] != 'CONFIRMED':
                    print("Booking not found or already cancelled")
                    return False

                price, _, flight_number, phone = result

                # Cancel the booking
                cursor.execute(
                    "UPDATE Bookings SET status = 'CANCELLED' WHERE booking_id = %s",
                    (booking_id,)
                )

                # Refund the user's balance through UserManager
                if self.user_manager.add_money(float(price)):
                    print(f"Refund of ${float(price):.2f} processed successfully")
                else:
                    raise Exception("Failed to process refund")

                # Update available seats for the flight
                cursor.execute("""
                    UPDATE Flights 
                    SET available_seats = available_seats + 1 
                    WHERE flight_number = %s
                """, (flight_number,))

                # Send cancellation confirmation SMS
                self.sms.send_cancellation_confirmation(phone, booking_id, flight_number)

                # Commit transaction
                connection.commit()
                print(f"Booking #{booking_id} cancelled successfully")
                return True

        except Exception as e:
            logging.error(f"Error in cancel_booking: {e}")
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            return False
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def view_bookings(self, user_id: int) -> List[Dict]:
        connection = None
        try:
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                query = """
                SELECT b.booking_id, b.flight_number, f.airline, 
                       f.departure_city, f.arrival_city, b.price, 
                       b.booking_date, b.food_choice, b.status
                FROM Bookings b
                JOIN Flights f ON b.flight_number = f.flight_number
                WHERE b.user_id = %s
                ORDER BY b.booking_date DESC, b.booking_id DESC
                """
                cursor.execute(query, (user_id,))
                results = cursor.fetchall()
                
                bookings = []
                for row in results:
                    booking = {
                        'booking_id': row[0],
                        'flight_number': row[1],
                        'airline': row[2],
                        'departure': row[3],
                        'arrival': row[4],
                        'price': float(row[5]),
                        'date': row[6],
                        'food_choice': row[7],
                        'status': row[8]
                    }
                    bookings.append(booking)
                return bookings
        except Exception as e:
            logging.error(f"Error in view_bookings: {e}")
            return []
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass


    def search_flights(self, origin: str, destination: str) -> List[Tuple]:
        connection = None
        try:
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                query = """
                SELECT flight_number, airline, price, available_seats 
                FROM Flights 
                WHERE departure_city = %s AND arrival_city = %s
                AND available_seats > 0
                """
                cursor.execute(query, (origin, destination))
                return cursor.fetchall()
        except Exception as e:
            logging.error(f"Error in search_flights: {e}")
            return []
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def select_food_option(self) -> str:
        options = ["Vegetarian Meal", "Chicken Meal", "Vegan Meal", "Gluten-Free Meal"]
        print("\nAvailable Food Options:")
        for idx, option in enumerate(options, 1):
            print(f"{idx}. {option}")
        while True:
            try:
                choice = int(input("Select a food option (1-4): "))
                if 1 <= choice <= len(options):
                    return options[choice - 1]
                print("Invalid choice. Please select between 1-4.")
            except ValueError:
                print("Please enter a number between 1-4.")

    def get_user_phone(self, user_id: int) -> str:
        connection = None
        try:
            connection = self.db.get_connection()
            with connection.cursor() as cursor:
                query = "SELECT phone FROM Users WHERE user_id = %s"
                cursor.execute(query, (user_id,))
                result = cursor.fetchone()
                return result[0] if result else ""
        except Exception as e:
            logging.error(f"Error in get_user_phone: {e}")
            return ""
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

def main():
    try:
        # Initialize managers
        db_manager = DatabaseManager()
        db_manager.initialize_tables()
        user_manager = UserManager(db_manager)
        flight_manager = FlightManager(db_manager, user_manager)

        while True:
            print("\n=== Flight Management System ===")
            print("1. Sign Up")
            print("2. Login")
            print("3. Exit")
            
            try:
                choice = input("Choose an option (1-3): ").strip()
            except EOFError:
                print("\nExiting system...")
                break

            if choice == '1':
                print("\n=== Sign Up ===")
                try:
                    username = input("Username: ").strip()
                    password = input("Password: ").strip()
                    name = input("Full Name: ").strip()
                    email = input("Email: ").strip()
                    phone = input("Phone Number (with country code): ").strip()
                    
                    if not all([username, password, name, email, phone]):
                        print("All fields are required. Please try again.")
                        continue
                    
                    if user_manager.signup(username, password, name, email, phone):
                        print("Signup successful! Please login.")
                    else:
                        print("Signup failed. Username might be taken or invalid details provided.")
                except Exception as e:
                    logging.error(f"Error during signup: {e}")
                    print("An error occurred during signup. Please try again.")

            elif choice == '2':
                print("\n=== Login ===")
                try:
                    username = input("Username: ").strip()
                    password = input("Password: ").strip()
                    user_id = user_manager.login(username, password)

                    if user_id:
                        print(f"\nWelcome back! Current balance: ${user_manager.get_user_balance():.2f}")
                        
                        while True:
                            print("\n=== Flight Booking Menu ===")
                            print("1. Search and Book Flights")
                            print("2. View My Bookings")
                            print("3. Cancel Booking")
                            print("4. Add Money to Wallet")
                            print("5. Check Balance")
                            print("6. Logout")

                            try:
                                sub_choice = input("Choose an option (1-6): ").strip()
                            except EOFError:
                                print("\nLogging out...")
                                break

                            if sub_choice == '1':
                                print("\n=== Flight Search ===")
                                try:
                                    origin = input("Enter departure city: ").strip()
                                    destination = input("Enter arrival city: ").strip()
                                    
                                    if not origin or not destination:
                                        print("Both departure and arrival cities are required.")
                                        continue
                                        
                                    flights = flight_manager.search_flights(origin, destination)

                                    if flights:
                                        print("\nAvailable Flights:")
                                        for idx, (flight_num, airline, price, available_seats) in enumerate(flights, 1):
                                            print(f"{idx}. {airline} ({flight_num})")
                                            print(f"   Price: ${price:.2f}")
                                            print(f"   Available Seats: {available_seats}")
                                            print(f"   Route: {origin} → {destination}")
                                            print()

                                        while True:
                                            try:
                                                flight_choice = input("\nSelect flight number (or 0 to cancel): ").strip()
                                                if flight_choice == '0':
                                                    break
                                                    
                                                flight_idx = int(flight_choice) - 1
                                                if 0 <= flight_idx < len(flights):
                                                    selected_flight = flights[flight_idx]
                                                    
                                                    # Show booking confirmation
                                                    print("\nBooking Details:")
                                                    print(f"Flight: {selected_flight[1]} ({selected_flight[0]})")
                                                    print(f"Price: ${selected_flight[2]:.2f}")
                                                    print(f"Route: {origin} → {destination}")
                                                    
                                                    confirm = input("\nConfirm booking? (yes/no): ").strip().lower()
                                                    if confirm == 'yes':
                                                        if flight_manager.book_flight(selected_flight[0], user_id):
                                                            print("\nBooking successful!")
                                                            print(f"Current balance: ${user_manager.get_user_balance():.2f}")
                                                        else:
                                                            print("\nBooking failed. Please try again.")
                                                    break
                                                else:
                                                    print("Invalid flight number. Please try again.")
                                            except ValueError:
                                                print("Please enter a valid number.")
                                    else:
                                        print("No flights found for this route.")
                                except Exception as e:
                                    logging.error(f"Error during flight booking: {e}")
                                    print("An error occurred during booking. Please try again.")

                            elif sub_choice == '2':
                                print("\n=== My Bookings ===")
                                bookings = flight_manager.view_bookings(user_id)
                                if bookings:
                                    for booking in bookings:
                                        print("\n------------------------")
                                        print(f"Booking ID: {booking['booking_id']}")
                                        print(f"Flight: {booking['airline']} ({booking['flight_number']})")
                                        print(f"Route: {booking['departure']} → {booking['arrival']}")
                                        print(f"Price: ${booking['price']:.2f}")
                                        print(f"Date: {booking['date']}")
                                        print(f"Status: {booking['status']}")
                                        print(f"Food Choice: {booking['food_choice']}")
                                        print("------------------------")
                                else:
                                    print("You don't have any bookings.")

                            elif sub_choice == '3':
                                print("\n=== Cancel Booking ===")
                                bookings = flight_manager.view_bookings(user_id)
                                if bookings:
                                    # Show only active bookings
                                    active_bookings = [b for b in bookings if b['status'] == 'CONFIRMED']
                                    if active_bookings:
                                        print("\nYour Active Bookings:")
                                        for booking in active_bookings:
                                            print(f"\nBooking ID: {booking['booking_id']}")
                                            print(f"Flight: {booking['airline']} ({booking['flight_number']})")
                                            print(f"Route: {booking['departure']} → {booking['arrival']}")
                                            print(f"Price: ${booking['price']:.2f}")
                                        
                                        try:
                                            booking_id = int(input("\nEnter Booking ID to cancel (or 0 to go back): "))
                                            if booking_id != 0:
                                                if flight_manager.cancel_booking(booking_id, user_id):
                                                    print("Booking cancelled successfully!")
                                                    print(f"New balance: ${user_manager.get_user_balance():.2f}")
                                                else:
                                                    print("Cancellation failed. Please try again.")
                                        except ValueError:
                                            print("Please enter a valid booking ID.")
                                    else:
                                        print("You don't have any active bookings to cancel.")
                                else:
                                    print("You don't have any bookings to cancel.")

                            elif sub_choice == '4':
                                print("\n=== Add Money to Wallet ===")
                                try:
                                    amount = float(input("Enter amount to add: $"))
                                    if amount <= 0:
                                        print("Please enter a positive amount.")
                                        continue
                                        
                                    if user_manager.add_money(amount):
                                        print(f"Successfully added ${amount:.2f}")
                                        print(f"New balance: ${user_manager.get_user_balance():.2f}")
                                    else:
                                        print("Failed to add money. Please try again.")
                                except ValueError:
                                    print("Please enter a valid amount.")

                            elif sub_choice == '5':
                                print(f"\nCurrent balance: ${user_manager.get_user_balance():.2f}")

                            elif sub_choice == '6':
                                print("\nLogging out...")
                                break

                            else:
                                print("Invalid choice. Please try again.")
                    else:
                        print("Login failed. Please check your credentials and try again.")
                except Exception as e:
                    logging.error(f"Error during login: {e}")
                    print("An error occurred during login. Please try again.")

            elif choice == '3':
                print("\nThank you for using the Flight Management System. Goodbye!")
                break

            else:
                print("Invalid choice. Please try again.")

    except Exception as e:
        logging.error(f"Critical error in main: {e}")
        print("A critical error occurred. Please restart the application.")
    finally:
        try:
            db_manager.get_connection().close()
        except:
            pass

if __name__ == "__main__":
    main()