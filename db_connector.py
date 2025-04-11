import pyodbc
import pandas as pd

# Your database connection parameters
SERVER = 'MID-PI-DARIUVLO\SQLEXPRESS'
DATABASE = 'AKENEO' 

# Function to connect to the database
def connect_db():
    conn_str = (
        f'DRIVER={{ODBC Driver 17 for SQL Server}};'
        f'SERVER={SERVER};'
        f'DATABASE={DATABASE};'
        'Trusted_Connection=yes;'
    )
    return pyodbc.connect(conn_str)

# Function to get the database schema
def get_db_schema():
    # Use the connect_db function to establish a connection
    conn = connect_db()
    cursor = conn.cursor()

    schema_info = {}

    # Query for tables
    cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE = 'BASE TABLE'")
    tables = cursor.fetchall()

    # For each table, get column names
    for table in tables:
        table_name = table[0]
        cursor.execute(f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{table_name}'")
        columns = cursor.fetchall()
        column_names = [col[0] for col in columns]
        schema_info[table_name] = column_names

    conn.close()

    # Format the schema information as a string
    formatted = "Tables:\n"
    for table, columns in schema_info.items():
        formatted += f"- {table} ({', '.join(columns)})\n"

    return formatted

# Function to run SQL query and return results as a pandas DataFrame
def run_sql_query(query: str):
    conn = connect_db()  # Use the connect_db function to connect
    return pd.read_sql(query, conn)
