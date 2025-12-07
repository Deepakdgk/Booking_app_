import os
import sqlite3
from datetime import datetime, date
import random
import calendar
from flask import Flask, render_template, request, redirect, jsonify, url_for, session, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret_key")  # Needed for session management

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "bookings.db")

# --- Time slots and bays ---
slots = [
    ("08:30", "09:30"),
    ("09:30", "10:30"),
    ("10:30", "11:30"),
    ("11:30", "12:30"),
    ("12:30", "13:30"),
    ("13:30", "14:30"),
    ("14:30", "15:30"),
    ("15:30", "16:30"),
    ("16:30", "17:30")
]
bays = [1, 2, 3]
tech_bays = [1, 2, 3]

# --- Database connection ---
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# ---------------- HOME PAGE ----------------
@app.route("/", methods=["GET"])
def index():
    today = date.today().isoformat()
    return render_template("index.html", bays=bays, slots=slots, today=today, search_result=None, search_list=None)

# ---------------- BOOK SLOT ----------------
@app.route("/book", methods=["POST"])
def book():
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    bay = request.form.get("bay")
    slot = request.form.get("slot")
    booking_date = request.form.get("booking_date")

    if not (name and phone and bay and slot and booking_date):
        return "Missing data", 400

    bay = int(bay)
    start_t, end_t = slot.split("-")
    slot_start_full = f"{booking_date} {start_t}:00"
    slot_end_full = f"{booking_date} {end_t}:00"
    booking_code = random.randint(10000, 99999)

    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT id FROM bookings WHERE bay=? AND slot_start=? AND canceled=0 AND closed=0",
                (bay, slot_start_full))
    if cur.fetchone():
        conn.close()
        return "This bay is already booked at that date/time.", 400

    cur.execute("""
        INSERT INTO bookings (name, phone, email, bay, booking_date, slot_start, slot_end, created_at, booking_code, canceled, tech_remark, closed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, '', 0)
    """, (name, phone, email, bay, booking_date, slot_start_full, slot_end_full, datetime.now().isoformat(), booking_code))
    conn.commit()
    conn.close()

    return redirect(url_for("index"))

# ---------------- SEARCH BOOKING ----------------
@app.route("/search", methods=["POST"])
def search_booking():
    phone = request.form.get("phone", "").strip()
    conn = get_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM bookings WHERE phone=? ORDER BY id DESC LIMIT 1", (phone,))
    latest = cur.fetchone()

    cur.execute("SELECT * FROM bookings WHERE phone=? ORDER BY id DESC", (phone,))
    booking_list = cur.fetchall()

    conn.close()
    return render_template("index.html", bays=bays, slots=slots, today=date.today().isoformat(),
                           search_result=latest, search_list=booking_list)

# ---------------- MANAGER LOGIN ----------------
@app.route("/manager/login", methods=["GET", "POST"])
def manager_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == "admin" and password == "Admin@123":
            session["manager_logged_in"] = True
            return redirect(url_for("manager"))
        flash("Invalid username or password!", "danger")
    return render_template("login.html")

@app.route("/manager/logout")
def manager_logout():
    session.pop("manager_logged_in", None)
    return redirect(url_for("manager_login"))

# ---------------- MANAGER TABLE VIEW + FILTER ----------------
@app.route("/manager")
def manager():
    if not session.get("manager_logged_in"):
        return redirect(url_for("manager_login"))

    filter_month = request.args.get("filter_month")  # yyyy-mm format
    conn = get_db()
    cur = conn.cursor()

    if filter_month:
        start = f"{filter_month}-01 00:00:00"
        end = f"{filter_month}-31 23:59:59"
        cur.execute("SELECT * FROM bookings WHERE datetime(slot_start) BETWEEN datetime(?) AND datetime(?) ORDER BY datetime(slot_start)", (start, end))
    else:
        cur.execute("SELECT * FROM bookings ORDER BY datetime(slot_start) ASC")

    rows = cur.fetchall()
    conn.close()

    return render_template("manager.html", rows=rows, filter_month=filter_month)

# ---------------- TECHNICIAN BAY VIEW ----------------
@app.route("/bay/<int:bay_id>")
def bay_page(bay_id):
    if bay_id not in tech_bays:
        return "Technician page only available for bays 1-3", 404
    sel_date = request.args.get("date", date.today().isoformat())
    return render_template("bay.html", bay_id=bay_id, sel_date=sel_date)

@app.route("/api/bay_bookings")
def api_bay_bookings():
    bay = request.args.get("bay")
    sel_date = request.args.get("date")
    if not bay or not sel_date:
        return jsonify({"error": "Missing bay or date"}), 400
    try:
        bay = int(bay)
    except ValueError:
        return jsonify({"error": "Invalid bay"}), 400

    start = f"{sel_date} 00:00:00"
    end = f"{sel_date} 23:59:59"

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, name, phone, slot_start, slot_end FROM bookings
        WHERE bay=? AND closed=0 AND canceled=0 AND datetime(slot_start) BETWEEN datetime(?) AND datetime(?)
        ORDER BY datetime(slot_start)
    """, (bay, start, end))
    rows = cur.fetchall()
    conn.close()
    bookings = [dict(r) for r in rows]
    return jsonify(bookings)

# ---------------- CLOSE BOOKING ----------------
@app.route("/api/close_booking", methods=["POST"])
def api_close_booking():
    booking_id = request.form.get("booking_id")
    remark = request.form.get("remark", "").strip()
    if not booking_id:
        return jsonify({"error": "Booking ID required"}), 400
    try:
        booking_id = int(booking_id)
    except ValueError:
        return jsonify({"error": "Invalid booking ID"}), 400

    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE bookings SET tech_remark=?, closed=1, closed_at=? WHERE id=?",
                (remark, datetime.now().isoformat(), booking_id))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

# ---------------- MANAGER CALENDAR VIEW ----------------
@app.route("/manager/calendar")
def manager_calendar():
    if not session.get("manager_logged_in"):
        return redirect(url_for("manager_login"))

    import calendar, sqlite3
    from datetime import datetime

    conn = sqlite3.connect("bookings.db")
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get month/year from request (dynamic navigation)
    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    # Default current month
    today = datetime.today()
    if not month or not year:
        month, year = today.month, today.year

    # Calendar matrix
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]

    # Query booking counts by date
    cur.execute("""
        SELECT booking_date,
               COUNT(*) AS total,
               SUM(CASE WHEN closed = 0 AND canceled = 0 THEN 1 ELSE 0 END) AS open_count
        FROM bookings
        GROUP BY booking_date
    """)
    data = {row["booking_date"]: {"total": row["total"], "open": row["open_count"]} for row in cur.fetchall()}

    return render_template("calendar.html", cal=cal, year=year, month=month,
                           month_name=month_name, data=data)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run()
