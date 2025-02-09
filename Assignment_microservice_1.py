from fastapi import FastAPI
import sqlite3
app = FastAPI()


def init_db():
    conn = sqlite3.connect("users.db")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    return conn

init_db()
 
def get_db_connection():
	conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute(
        """CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT
        )"""
    )
    conn.commit()
    conn.close()




@app.get("/")
def read_root():
    return {"message": "Welcome to the User Management API"}


@app.post("/add_user/")
def add_user(username: str, password: str):
	try :
		conn = get_db_connection()
		cursor = conn.cursor()
		
		# Check if the user already exists
		cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
		user = cursor.fetchone()
		
		if user:
			# Update password if user exists
			cursor.execute("UPDATE users SET password = ? WHERE username = ?", (password, username))
			message = "User password updated successfully"
		else:
			# Insert new user
			cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
			message = "User added successfully"

		conn.commit()
		conn.close()
		return {"message": message, "username" : username }
	except Exception :
	    return { "Exception" : Exception }
		


@app.get("/get_users/")
def get_users():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password FROM users")
    users = cursor.fetchall()
    conn.close()
	 if not users:
        return {"message": "No users found in the database"}
    return {"users": [user[1] for user in users]}
    #return {"users": users}







		
#curl http:/192.168.1.10:8000/		
#curl http:/192.168.1.10:8000/get_users/		
#curl -X POST "http://192.168.1.10:8000/add_user/?username=testuser&password=pass123"
		
		
    	
