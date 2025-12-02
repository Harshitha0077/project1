import re
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

from flask import (
    Flask, render_template, url_for, request,
    redirect, session
)
from project1.DBConnection import Db

app = Flask(__name__)
app.secret_key = "123"

# ================== COMMON ==================

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/find_your_charger')
def find_your_charger():
    return render_template('find_your_charger.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact_us', methods=['GET', 'POST'])
def contact_us():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        feedback = request.form['message']
        db = Db()
        db.insert(
            "INSERT INTO contact_us (Name, Email, feedback_date, feedback) "
            "VALUES (%s, %s, NOW(), %s)",
            (name, email, feedback)
        )
        return render_template('contact_us.html', message='Thank you for your feedback!')
    return render_template('contact_us.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == "POST":
        email = request.form.get('email', '').strip()
        if not email:
            return "Email is required", 400
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            return "Invalid email format", 400

        db = Db()
        user = db.selectOne("SELECT * FROM login WHERE email=%s", (email,))
        if not user:
            return "Sorry, we couldn't find an account associated with that email address.", 400

        password = user['password']
        sender_email = "a97298570@gmail.com"
        sender_password = "56B50C32C322385ED3009518610638823005"
        recipient_email = email
        subject = "Password Reset for EV STATION BOOKING WEBSITE"
        content = f"Your password for EV STATION BOOKING WEBSITE is: {password}"

        host = "smtp.gmail.com"
        port = 465
        message = MIMEMultipart()
        message['From'] = Header(sender_email)
        message['To'] = Header(recipient_email)
        message['Subject'] = Header(subject)
        message.attach(MIMEText(content, 'plain', 'utf-8'))

        try:
            with smtplib.SMTP_SSL(host, port) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipient_email, message.as_string())
            return "An email has been sent to your email address with your password."
        except smtplib.SMTPAuthenticationError:
            return "Failed to authenticate with the email server. Please check your email credentials.", 500
        except smtplib.SMTPException as e:
            return f"An error occurred while sending the email: {str(e)}", 500

    return render_template("forgot_password.html")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('user_type') == "admin":
        return redirect('/admin-home')

    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        db = Db()
        ss = db.selectOne(
            "SELECT * FROM login WHERE username=%s AND password=%s",
            (username, password)
        )
        if ss is None:
            return '''<script>alert('user not found');window.location="/login"</script>'''

        session['username'] = username
        if ss['usertype'] == 'admin':
            session['user_type'] = 'admin'
            return redirect('/admin-home')
        elif ss['usertype'] == 'user':
            session['user_type'] = 'user'
            session['uid'] = ss['login_id']
            return redirect('/user-dashboard')
        else:
            return '''<script>alert('user not found');window.location="/login"</script>'''

    return render_template("login.html")

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form['signupUsername']
        email = request.form['email']
        password = request.form['password']
        confirmPassword = request.form['confirmPassword']

        if not username.strip():
            return redirect(url_for('register', error='Please enter a username', form_id='createAccount'))
        if not email.strip():
            return redirect(url_for('register', error='Please enter an email address', form_id='createAccount'))
        if not password.strip():
            return redirect(url_for('register', error='Please enter a password', form_id='createAccount'))
        if not confirmPassword.strip():
            return redirect(url_for('register', error='Please confirm the password', form_id='createAccount'))
        if password != confirmPassword:
            return redirect(url_for('register', error='Passwords do not match', form_id='createAccount'))

        db = Db()
        login_id = db.insert(
            "INSERT INTO login (username, password, usertype) VALUES (%s, %s, 'user')",
            (username, password)
        )
        # optional user table insert – only if such a table exists
        try:
            db.insert(
                "INSERT INTO user (login_id, name, email) VALUES (%s, %s, %s)",
                (login_id, username, email)
            )
        except Exception:
            pass

        return '<script>alert("User registered"); window.location.href="/login";</script>'

    error = request.args.get('error')
    return render_template("login.html", error=error, form_id='createAccount')

# ================== USER DASHBOARD & PROFILE ==================

@app.route('/user-dashboard')
def user_dashboard():
    if session.get('user_type') != "user":
        return redirect('/')
    username = session['username']
    db = Db()
    bookings = db.select(
        "SELECT Booking_id, Booking_date, Time_from, Time_to, City, Station_name, Available_ports "
        "FROM booking WHERE login_id = %s ORDER BY Booking_date DESC",
        (session['uid'],)
    )
    return render_template("user/user-login-dashboard.html",
                           bookings=bookings, username=username)

@app.route('/usr_delete_booking/<int:booking_id>')
def usr_delete_booking(booking_id):
    if session.get('user_type') != "user":
        return redirect('/user-dashboard')
    db = Db()
    db.delete(
        "DELETE FROM booking WHERE booking_id = %s AND login_id = %s",
        (booking_id, session['uid'])
    )
    return '''<script>alert('Booking deleted');window.location="/user-dashboard"</script>'''

@app.route('/user-profile', methods=['GET', 'POST'])
def user_profile():
    if session.get('user_type') != 'user':
        return redirect('/')

    db = Db()

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']  # currently not stored; kept for future
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            return redirect(url_for('user_profile', error='Passwords do not match'))

        # Update only login table (username + password)
        db.update(
            "UPDATE login SET username=%s, password=%s WHERE login_id=%s",
            (name, password, session['uid'])
        )

        return '<script>alert("Account details updated"); window.location.href="/user-profile";</script>'

    user = db.selectOne(
        "SELECT username AS name FROM login WHERE login_id=%s",
        (session['uid'],)
    )
    error = request.args.get('error')
    return render_template('user/user-profile.html', user=user, error=error)

# ================== USER STATION SEARCH & BOOKING ==================

@app.route('/user_find_your_charger', methods=['GET', 'POST'])
def user_find_your_charger():
    if session.get('user_type') != 'user':
        return redirect('/')
    if request.method == 'POST':
        city = request.form.get('City')
        charger_type = request.form.get('Charger_type')
        db = Db()
        qry = db.select(
            "SELECT Station_name, Address, Charger_type, Available_ports "
            "FROM admin_charging_station_list WHERE City = %s AND Charger_type = %s",
            (city, charger_type)
        )
        return render_template('user/station_search.html', data=qry,
                               City=city, Charger_type=charger_type)
    return render_template('user/user_find_your_charger.html')

@app.route('/search_stations', methods=['POST'])
def search_stations():
    City = request.form.get('City')
    Charger_type = request.form.get('Charger_type')
    return redirect(url_for('station_search', City=City, Charger_type=Charger_type))

@app.route('/station_search', methods=['GET'])
def station_search():
    if session.get('user_type') != 'user':
        return redirect('/')
    City = request.args.get('City')
    Charger_type = request.args.get('Charger_type')
    db = Db()
    ss = db.select(
        "SELECT * FROM admin_charging_station_list WHERE City = %s AND Charger_type = %s",
        (City, Charger_type)
    )
    return render_template('user/station_search.html',
                           data=ss, City=City, Charger_type=Charger_type)

@app.route('/booking', methods=['GET', 'POST'])
def booking():
    if request.method == 'POST':
        Station_name = request.form['Station_name']
        City = request.form['City']
        Available_ports = request.form['Available_ports']
        return redirect(url_for('booking_form',
                                Station_name=Station_name,
                                City=City,
                                Available_ports=Available_ports))
    Station_name = request.args.get('Station_name')
    City = request.args.get('City')
    Available_ports = request.args.get('Available_ports')
    return redirect(url_for('booking_form',
                            Station_name=Station_name,
                            City=City,
                            Available_ports=Available_ports))

@app.route('/booking-form', methods=['GET'])
def booking_form():
    if session.get('user_type') != 'user':
        return redirect('/')
    city = request.args.get('City')
    available_ports = request.args.get('Available_ports')
    station_name = request.args.get('Station_name')
    db = Db()
    station_data = db.select(
        "SELECT * FROM admin_charging_station_list WHERE Station_name = %s",
        (station_name,)
    )
    session['station_data'] = station_data[0] if station_data else None
    if session.get('station_data'):
        return render_template('user/booking_form.html',
                               city=city, available_ports=available_ports)
    return redirect(url_for('station_search'))

@app.route('/book', methods=['POST'])
def book():
    if session.get('user_type') != 'user':
        return redirect('/booking-form')

    station_name = request.form['Station_name']
    city = request.form['City']
    available_ports = request.form['Available_ports']
    booking_date = request.form['Booking_date']
    time_from = request.form['Time_from']
    time_to = request.form['Time_to']
    login_id = session['uid']

    db = Db()
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    sql = ("INSERT INTO booking "
           "(Station_name, City, Available_ports, Booking_date, Time_from, Time_to, Created_id, login_id) "
           "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)")
    db.insert(sql, (station_name, city, available_ports,
                    booking_date, time_from, time_to,
                    created_at, login_id))

    return redirect('/user-dashboard')

if __name__ == "__main__":
    app.run(debug=False)
