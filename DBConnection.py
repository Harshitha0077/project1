# DBConnection.py

import mysql.connector
from mysql.connector import Error

class Db:
    def __init__(self):
        try:
            self.cnx = mysql.connector.connect(
                host="db",          # MySQL service name from docker-compose
                port=3306,
                user="root",
                password="",
                database="ev_db"
            )
            self.cur = self.cnx.cursor(dictionary=True, buffered=True)
            print("✅ Database connected successfully!")
        except Error as e:
            print(f"❌ Database connection failed: {e}")
            # Re-raise so routes can handle it
            raise

    def select(self, q, params=None):
        self.cur.execute(q, params)
        return self.cur.fetchall()

    def selectOne(self, q, params=None):
        self.cur.execute(q, params)
        return self.cur.fetchone()

    def insert(self, q, params=None):
        self.cur.execute(q, params)
        self.cnx.commit()
        return self.cur.lastrowid

    def update(self, q, params=None):
        self.cur.execute(q, params)
        self.cnx.commit()
        return self.cur.rowcount

    def delete(self, q, params=None):
        self.cur.execute(q, params)
        self.cnx.commit()
        return self.cur.rowcount

    def close(self):
        if hasattr(self, "cur") and self.cur:
            self.cur.close()
        if hasattr(self, "cnx") and self.cnx and self.cnx.is_connected():
            self.cnx.close()
            print("✅ Database connection closed.")
