import os
import io
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Train, Booking

# PDF Generation Imports
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import inch
from reportlab.lib import colors

app = Flask(__name__)
app.config['SECRET_KEY'] = 'railease_ultimate_secret_key_888'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Initialize Database and Seed Sample Trains
with app.app_context():
    db.create_all()
    
    # Check if seeding is complete
    cities = ['Mumbai', 'Pune', 'Delhi', 'Nagpur', 'Chennai', 'Bangalore', 'Hyderabad', 'Ahmedabad', 'Kolkata', 'Jaipur']
    
    # Categories for different train types
    categories = [
        {'prefix': 'Rajdhani Express', 'price_base': 2800, 'seats': 120, 'fast': True},
        {'prefix': 'Vande Bharat Express', 'price_base': 2100, 'seats': 80, 'fast': True},
        {'prefix': 'Shatabdi Express', 'price_base': 950, 'seats': 100, 'fast': True},
        {'prefix': 'Duronto Express', 'price_base': 2400, 'seats': 130, 'fast': True},
        {'prefix': 'Tejas Express', 'price_base': 1600, 'seats': 75, 'fast': True},
        {'prefix': 'Humsafar Express', 'price_base': 1550, 'seats': 140, 'fast': False},
        {'prefix': 'Garib Rath Express', 'price_base': 1100, 'seats': 150, 'fast': False},
        {'prefix': 'Jan Shatabdi Express', 'price_base': 850, 'seats': 150, 'fast': False}
    ]

    import random
    
    new_trains = []
    
    # Establish complete connectivity between all city pairs
    for src in cities:
        for dest in cities:
            if src == dest:
                continue
            
            # Check existing trains for this specific route
            existing_count = Train.query.filter_by(source=src, destination=dest).count()
            
            # We want at least 3 trains per route for variety
            if existing_count < 3:
                to_add = 3 - existing_count
                
                # Pricing factor based on a rough distance heuristic using city index differences
                dist_shift = abs(cities.index(src) - cities.index(dest))
                
                for k in range(to_add):
                    # Select a category based on index k to ensure variety per route
                    # e.g., k=0 gets premium, k=1 gets superfast, k=2 gets express
                    if k == 0:
                        cat = categories[random.randint(0, 2)] # Premium
                    elif k == 1:
                        cat = categories[random.randint(3, 4)] # Fast
                    else:
                        cat = categories[random.randint(5, 7)] # Regular
                    
                    price = cat['price_base'] + (dist_shift * 200) + random.randint(-50, 50)
                    
                    # Morning, Afternoon, and Night timings
                    # Based on k: k=0 Morning, k=1 Afternoon, k=2 Night
                    if k == 0:
                        dep_h = random.randint(5, 10)
                    elif k == 1:
                        dep_h = random.randint(11, 17)
                    else:
                        dep_h = random.randint(18, 23)
                    
                    dep_min = random.choice(['00', '15', '30', '45'])
                    dep_time = f"{dep_h:02d}:{dep_min}"
                    
                    # Calculate arrival (simplified heuristic: distance + speed)
                    travel_time = dist_shift * 2 + (1 if not cat['fast'] else 0) + 1
                    arr_h = (dep_h + travel_time) % 24
                    arr_time = f"{arr_h:02d}:{(int(dep_min) + 30) % 60:02d}"
                    
                    # Unique train name using route and category
                    train_name = f"{cat['prefix']} - {src[:3].upper()}{dest[:3].upper()}-{k+1}"
                    
                    new_trains.append(Train(
                        name=train_name,
                        source=src,
                        destination=dest,
                        departure_time=dep_time,
                        arrival_time=arr_time,
                        price=float(price),
                        total_seats=cat['seats']
                    ))

    if new_trains:
        db.session.bulk_save_objects(new_trains)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('This email is already registered. Please login.', 'danger')
            return redirect(url_for('signup'))
            
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(name=name, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash(f'Welcome back, {user.name}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Invalid email or password. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/search', methods=['GET'])
def search():
    source = request.args.get('from', '').strip()
    destination = request.args.get('to', '').strip()
    date = request.args.get('date', '')
    session['search_date'] = date # Store for booking flow
    
    # Query trains based on source and destination (case-insensitive)
    trains = Train.query.filter(
        Train.source.ilike(f'%{source}%'),
        Train.destination.ilike(f'%{destination}%')
    ).all()
    
    return render_template('results.html', trains=trains, source=source, dest=destination, date=date)

@app.route('/booking/<int:train_id>')
@login_required
def booking(train_id):
    train = Train.query.get_or_404(train_id)
    date = session.get('search_date', 'Not Selected')
    # Fetch seats already booked for this train on this specific date
    booked_seats = [b.seat_no for b in Booking.query.filter_by(train_id=train_id, booking_date=date).all()]
    return render_template('booking.html', train=train, booked_seats=booked_seats, date=date)

@app.route('/payment', methods=['POST'])
@login_required
def payment():
    train_id = request.form.get('train_id')
    seat_no = request.form.get('seat_no')
    date = request.form.get('date')
    train = Train.query.get(train_id)
    if not train or not seat_no:
        flash('Session expired or invalid data. Please try again.', 'warning')
        return redirect(url_for('index'))
    return render_template('payment.html', train=train, seat_no=seat_no, date=date)

@app.route('/confirm_booking', methods=['POST'])
@login_required
def confirm_booking():
    train_id = request.form.get('train_id')
    seat_no = request.form.get('seat_no')
    date = request.form.get('date')
    
    # Final write to database
    new_booking = Booking(
        user_id=current_user.id,
        train_id=train_id,
        seat_no=seat_no,
        booking_date=date
    )
    db.session.add(new_booking)
    db.session.commit()
    flash('Ticket Booked Successfully!', 'success')
    return render_template('confirmation.html', booking=new_booking)

@app.route('/dashboard')
@login_required
def dashboard():
    # Show bookings for the logged-in user, newest first
    user_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.id.desc()).all()
    return render_template('dashboard.html', bookings=user_bookings)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/download_ticket/<int:booking_id>')
@login_required
def download_ticket(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    
    # Security check: Ensure user owns this booking
    if booking.user_id != current_user.id:
        flash('Unauthorized access.', 'danger')
        return redirect(url_for('dashboard'))
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A5)
    width, height = A5

    # Header / Branding
    p.setFillColor(colors.black)
    p.rect(0, height - 1*inch, width, 1*inch, fill=1)
    
    p.setFillColor(colors.white)
    p.setFont("Helvetica-Bold", 24)
    p.drawCentredString(width / 2, height - 0.65*inch, "RAILEASE")
    
    p.setFont("Helvetica-Bold", 10)
    p.drawCentredString(width / 2, height - 0.85*inch, "PREMIUM RAILWAY BOARDING PASS")

    # Content
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Bold", 12)
    y_position = height - 1.5*inch
    
    def draw_field(label, value, y):
        p.setFont("Helvetica-Bold", 9)
        p.setStrokeColor(colors.grey)
        p.drawString(0.5*inch, y, label.upper())
        p.setFont("Helvetica", 11)
        p.drawString(0.5*inch, y - 0.2*inch, str(value))
        return y - 0.5*inch

    y_position = draw_field("Passenger Name", booking.user_ref.name, y_position)
    y_position = draw_field("Train Service", booking.train.name, y_position)
    y_position = draw_field("Route", f"{booking.train.source} -> {booking.train.destination}", y_position)
    y_position = draw_field("Journey Date", booking.booking_date, y_position)
    y_position = draw_field("Seat Allocation", booking.seat_no, y_position)
    y_position = draw_field("Booking Reference", f"RE-{booking.id:05d}", y_position)
    y_position = draw_field("Status", "CONFIRMED", y_position)

    # Footer
    p.setDash(3, 3)
    p.line(0.5*inch, 1*inch, width - 0.5*inch, 1*inch)
    p.setFont("Helvetica-Oblique", 8)
    p.drawCentredString(width / 2, 0.75*inch, "Thank you for choosing RailEase Elite Service.")
    p.drawCentredString(width / 2, 0.6*inch, "Please carry this PDF during your journey.")

    p.showPage()
    p.save()

    buffer.seek(0)
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f"RailEase_Ticket_{booking.id}.pdf",
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
