from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "supersecretkey"

# ===========================
# DATABASE CONFIGURATION
# ===========================
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///feedback.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# ===========================
# EMAIL CONFIGURATION
# ===========================
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'adefaratiadeniran@gmail.com'       # ✏️ replace with your Gmail
app.config['MAIL_PASSWORD'] = 'ikoljscizblafijm'          # ✏️ generated app password
app.config['MAIL_DEFAULT_SENDER'] = ('BagIn Support', 'adefaratiadeniran@gmail.com')

mail = Mail(app)

# ===========================
# MODELS
# ===========================
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(10), default="user")

class Complaint(db.Model):
    __tablename__ = 'complaints'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default="Pending")
    date_created = db.Column(db.DateTime, default=datetime.utcnow)

# ===========================
# MAIN ROUTES
# ===========================
@app.route('/')
def home():
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already exists, please login.')
            return redirect(url_for('login'))

        new_user = User(name=name, email=email, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully. Please log in.')
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.id
            session['user_name'] = user.name
            flash('Login successful!')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password.')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', name=session['user_name'])


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.')
    return redirect(url_for('login'))


# ===========================
# COMPLAINT ROUTES
# ===========================
@app.route('/complaints', methods=['GET', 'POST'])
def complaints():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        new_complaint = Complaint(user_id=session['user_id'], title=title, description=description)
        db.session.add(new_complaint)
        db.session.commit()
        flash('Complaint submitted successfully!')
        return redirect(url_for('complaints'))

    all_complaints = Complaint.query.filter_by(user_id=session['user_id']).all()
    return render_template('complaints.html', complaints=all_complaints, name=session['user_name'])


@app.route('/admin')
def admin():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    all_complaints = Complaint.query.all()
    return render_template('admin.html', complaints=all_complaints, name=user.name)


@app.route('/update_status/<int:complaint_id>/<status>')
def update_status(complaint_id, status):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role != 'admin':
        flash('Access denied.')
        return redirect(url_for('dashboard'))

    complaint = Complaint.query.get_or_404(complaint_id)
    complaint.status = status
    db.session.commit()
    flash('Complaint status updated.')
    return redirect(url_for('admin'))

# ===========================
# EXTERNAL FEEDBACK ROUTE (from BagIn website)
# ===========================
@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    """
    Receives feedback from BagIn Website (contactUs.html)
    Saves it in the database and redirects to thankyou.html
    """
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    # Create or reuse a guest user for website feedback
    guest_user = User.query.filter_by(email=email).first()
    if not guest_user:
        guest_user = User(name=name or "Guest User", email=email, password="none")
        db.session.add(guest_user)
        db.session.commit()

    new_feedback = Complaint(
        user_id=guest_user.id,
        title=f"Feedback from {name}",
        description=message,
        status="Pending"
    )
    db.session.add(new_feedback)
    db.session.commit()

    # Redirect to BagIn website thankyou page
    return redirect("http://127.0.0.1:5501/thankyou.html")

# ===========================
# CONTACT FORM (BagIn Website)
# ===========================
@app.route('/submit_contact', methods=['POST'])
def submit_contact():
    name = request.form.get('name')
    email = request.form.get('email')
    message = request.form.get('message')

    # Save to database
    new_complaint = Complaint(
        user_id=1,  # Default admin user
        title=f"Feedback from {name}",
        description=f"Email: {email}\n\nMessage:\n{message}",
        status="Pending"
    )
    db.session.add(new_complaint)
    db.session.commit()

    # ======================
    # Send notification email
    # ======================
    try:
        msg = Message(
            subject=f"📩 New Feedback from {name}",
            sender=app.config['MAIL_DEFAULT_SENDER'],
            recipients=["adefaratiadeniran@gmail.com"],  # Your receiving email
            body=f"""
Hello BagIn Admin,

You just got a new message from your website contact form.

-------------------------------------
Name: {name}
Email: {email}
Message:
{message}
-------------------------------------

Go check your admin dashboard for details.
            """
        )
        mail.send(msg)
        print("✅ Email sent successfully!")
    except Exception as e:
        print("❌ Email failed:", e)

    # Redirect user to thank-you page on your BagIn website
    return redirect("http://127.0.0.1:5500/Bagin%20Website/thankyou.html")

# ===========================
# RUN THE APP
# ===========================
if __name__ == "__main__":
    app.run(debug=True)
