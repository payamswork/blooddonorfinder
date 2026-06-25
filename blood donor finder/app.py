import sqlite3

from flask import Flask, render_template, request, redirect, session

app = Flask(__name__)
app.secret_key = "blood_donor_secret"

DATABASE = "blood_donors.db"

# ---------------------------------------------------
# Create database and table
# ---------------------------------------------------
def create_database():

    conn = sqlite3.connect(DATABASE)

    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS donors(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Name TEXT,
        Gender TEXT,
        Age INTEGER,
        Email TEXT,
        Phone INTEGER,           
        District TEXT,
        City TEXT,
        Blood_group TEXT,
        Months_since_last_donation INTEGER
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     username TEXT UNIQUE NOT NULL,
     email TEXT UNIQUE NOT NULL,
     password TEXT NOT NULL
    )
    """)

    conn.commit()
    conn.close()






# ---------------------------------------------------
# Home Page
# ---------------------------------------------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------------------------------
# Register Donor
# ---------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
     if "username" not in session:
        return redirect("/signup")


     if request.method == "POST":

        name = request.form["name"]
        gender = request.form["gender"]
        age = request.form["age"]
        email = request.form["email"]
        phone = request.form["phone"]
        district = request.form["district"]
        city = request.form["city"]
        blood_group = request.form["blood_group"]
        months = request.form["months"]

        conn = sqlite3.connect(DATABASE)

        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO donors
        (Name, Gender, Age, Email, Phone,
         District, City,
         Blood_group,
         Months_since_last_donation)

        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,

        (
            name,
            gender,
            age,
            email,
            phone,
            district,
            city,
            blood_group,
            months
        ))

        conn.commit()
        conn.close()

        return render_template("success.html")

     return render_template("register.html")


# ---------------------------------------------------
# Search Donors
# ---------------------------------------------------
@app.route("/search", methods=["GET", "POST"])
def search():

    donors = []

    if request.method == "POST":

        blood_group = request.form["blood_group"]

        conn = sqlite3.connect(DATABASE)

        cursor = conn.cursor()

        cursor.execute("""
        SELECT * FROM donors
        WHERE Blood_group=?
        """, (blood_group,))

        donors = cursor.fetchall()

        conn.close()

    return render_template("search.html", donors=donors)



#  SIGNUP ROUTE 
@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form["username"]
        email = request.form["email"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        try:

         cursor.execute(
          """
          INSERT INTO users(username,email,password)
          VALUES(?,?,?)
          """,
          (username, email, password)
         )
         
         conn.commit()
   

         session["username"] = username
         conn.close()
   
         return redirect("/register")

        except sqlite3.IntegrityError:

            conn.close()

            return "Username or Email already exists"

    return render_template("signup.html")

    

   

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT * FROM users
            WHERE username=? AND password=?
            """,
            (username, password)
        )

        user = cursor.fetchone()

        conn.close()

        if user:
             session["username"] = username
             return redirect("/")
        else:
            return "Invalid Username or Password"

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------------------------------------------
# Start application
# ---------------------------------------------------
if __name__ == "__main__":

    create_database()


    app.run(debug=True)