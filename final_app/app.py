from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import csv
import os

# ---------------------------------------------------------------------------
# Vercel runs serverless — the working directory is read-only except /tmp.
# We copy donors.db (bundled with the repo) into /tmp on first cold start.
# ---------------------------------------------------------------------------

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_DB   = os.path.join(BASE_DIR, "donors.db")   # read-only, shipped in repo
TMP_DB    = "/tmp/donors.db"                        # writable copy at runtime
CSV_FILE  = os.path.join(BASE_DIR, "donors.csv")

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, "templates"))
app.secret_key = os.environ.get("SECRET_KEY", "blooddonorjk2025_secure")


def get_db_path():
    """Return the writable DB path, seeding from the repo copy if needed."""
    if not os.path.exists(TMP_DB):
        if os.path.exists(REPO_DB):
            import shutil
            shutil.copy2(REPO_DB, TMP_DB)
        # Create fresh schema + seed from CSV if no repo DB either
        _bootstrap_db(TMP_DB)
    return TMP_DB


def _bootstrap_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS donors (
            id    INTEGER PRIMARY KEY AUTOINCREMENT,
            Name  TEXT    NOT NULL,
            Gender TEXT,
            Age   INTEGER,
            Email TEXT,
            Phone TEXT,
            District TEXT,
            City  TEXT,
            Blood_group TEXT,
            Months_since_last_donation INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email    TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)
    conn.commit()

    # Seed from CSV if donors table is empty
    count = conn.execute("SELECT COUNT(*) FROM donors").fetchone()[0]
    if count == 0 and os.path.exists(CSV_FILE):
        with open(CSV_FILE, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                conn.execute("""
                    INSERT INTO donors
                        (Name, Gender, Age, Email, Phone, District, City,
                         Blood_group, Months_since_last_donation)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (
                    row.get("Name", ""),
                    row.get("Gender", ""),
                    row.get("Age", 0),
                    row.get("Email", ""),
                    row.get("Phone", ""),
                    row.get("District", ""),
                    row.get("City", ""),
                    row.get("Blood_group", ""),
                    row.get("Months_since_last_donation", 0),
                ))
        conn.commit()
    conn.close()


def get_db():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form["username"].strip()
        email    = request.form["email"].strip()
        password = generate_password_hash(request.form["password"])
        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?,?,?)",
                (username, email, password)
            )
            conn.commit()
            session["username"] = username
            flash("Account created. Welcome.", "success")
            return redirect(url_for("register"))
        except sqlite3.IntegrityError:
            flash("Username or email already exists.", "error")
        finally:
            conn.close()
    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()
        conn.close()
        if user and check_password_hash(user["password"], password):
            session["username"] = username
            flash(f"Welcome back, {username}.", "success")
            return redirect(url_for("home"))
        else:
            flash("Invalid username or password.", "error")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if "username" not in session:
        flash("Please log in to register a donor.", "info")
        return redirect(url_for("login"))
    if request.method == "POST":
        name  = request.form["name"].strip()
        blood = request.form["blood_group"]
        if not name or not blood:
            flash("Name and Blood Group are required.", "error")
            return redirect(url_for("register"))
        conn = get_db()
        conn.execute("""
            INSERT INTO donors
                (Name, Gender, Age, Email, Phone, District, City,
                 Blood_group, Months_since_last_donation)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            name,
            request.form.get("gender", ""),
            request.form.get("age") or None,
            request.form.get("email", "").strip(),
            request.form.get("phone", "").strip(),
            request.form.get("district", ""),
            request.form.get("city", "").strip(),
            blood,
            request.form.get("months") or None,
        ))
        conn.commit()
        conn.close()
        return redirect(url_for("success"))
    return render_template("register.html")


@app.route("/success")
def success():
    return render_template("success.html")


@app.route("/search", methods=["GET", "POST"])
def search():
    donors     = []
    searched   = False
    query_bg   = ""
    query_dist = ""
    if request.method == "POST":
        query_bg   = request.form.get("blood_group", "").strip()
        query_dist = request.form.get("district", "").strip()
        searched   = True
        conn = get_db()
        if query_dist:
            donors = conn.execute("""
                SELECT * FROM donors
                WHERE Blood_group = ? AND District = ?
                ORDER BY Months_since_last_donation ASC
            """, (query_bg, query_dist)).fetchall()
        else:
            donors = conn.execute("""
                SELECT * FROM donors
                WHERE Blood_group = ?
                ORDER BY Months_since_last_donation ASC
            """, (query_bg,)).fetchall()
        conn.close()
    conn = get_db()
    districts = [r[0] for r in conn.execute(
        "SELECT DISTINCT District FROM donors ORDER BY District"
    ).fetchall()]
    conn.close()
    return render_template("search.html",
                           donors=donors, searched=searched,
                           query_bg=query_bg, query_dist=query_dist,
                           districts=districts)


@app.route("/donors")
def all_donors():
    page     = max(1, int(request.args.get("page", 1)))
    per_page = 20
    offset   = (page - 1) * per_page
    conn  = get_db()
    total = conn.execute("SELECT COUNT(*) FROM donors").fetchone()[0]
    rows  = conn.execute(
        "SELECT * FROM donors ORDER BY id DESC LIMIT ? OFFSET ?",
        (per_page, offset)
    ).fetchall()
    conn.close()
    total_pages = max(1, (total + per_page - 1) // per_page)
    return render_template("donors.html",
                           donors=rows, page=page,
                           total_pages=total_pages, total=total)


if __name__ == "__main__":
    _bootstrap_db(TMP_DB)
    app.run(debug=True)
