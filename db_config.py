import mysql.connector
from mysql.connector import Error

# Database connection configuration
db_config = {
    'user': 'root',
    'password': '',
    'host': '127.0.0.1',
    'database': 'document_edit_tool',
}

def get_db_connection():
    """
    Returns a connection to the MySQL database.
    """
    try:
        conn = mysql.connector.connect(**db_config)
        if conn.is_connected():
            print('Connection to MySQL database established successfully.')
            return conn
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
        return None
