from flask_login import UserMixin
import mysql.connector
import hashlib


class Database():

    def __init__(self):
        # Establish connection to MySQL
        self.mydb = mysql.connector.connect(
            host="localhost",
            user="your_username",
            password="your_password"
        )

        # Create a cursor object
        self.mycursor = self.mydb.cursor()
        self.setDB()

    def setDB(self):
        
        # Create the database
        self.mycursor.execute("CREATE DATABASE IF NOT EXISTS user_login_db")

        # Switch to the newly created database
        self.mycursor.execute("USE user_login_db")

        # Create the users table
        self.mycursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password VARCHAR(255) NOT NULL,
            email VARCHAR(100) UNIQUE NOT NULL
        )
        """)

        # Commit the changes
        self.mydb.commit()

    def contains_email(self, email):
       
        try: 
            # Execute a SELECT query to check for the email
            query = "SELECT COUNT(*) FROM users WHERE email = %s"
            self.mycursor.execute(query, (email,))
            
            # Fetch the result
            result = self.mycursor.fetchone()
            
            # If the count is greater than 0, the email exists
            return result[0] > 0
        
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return False

    def register_email(self, email):
      
        try:
            self.mycursor.execute("SELECT passwd FROM self.mydb WHERE email = '%s'", (email))
            row = self.mycursor.fetchone()
            user_passwd = row[0]
            self.mycursor.execute("""
            INSERT INTO users (email)
            VALUES (%s)
            """, (email))
            self.mydb.commit()
            return True
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return False
        
    def register_user(self, username, password, email):
        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            self.mycursor.execute("""
            INSERT INTO users (username, password, email)
            VALUES (%s, %s, %s)
            """, (username, hashed_password, email))
            self.mydb.commit()
            return True
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            return False
        
    def login_user(self, username, password):
        # Hash the password
        hashed_password = hashlib.sha256(password.encode()).hexdigest()
        
        self.mycursor.execute("""
        SELECT * FROM users
        WHERE username = %s AND password = %s
        """, (username, hashed_password))
        
        user = self.mycursor.fetchone()
        return user is not None