from flask import Flask, render_template, request, flash, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime
from functools import wraps
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'aurelian-secret-2024-x9k')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///aurelian.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Mail config — set MAIL_USERNAME and MAIL_PASSWORD as environment variables
app.config['MAIL_SERVER']   = 'smtp.gmail.com'
app.config['MAIL_PORT']     = 587
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', '')

db   = SQLAlchemy(app)
mail = Mail(app)

# ─────────────────────────────────────────────
# MODEL
# ─────────────────────────────────────────────

class Lead(db.Model):
    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(120), nullable=False)
    email        = db.Column(db.String(200), nullable=False)
    company      = db.Column(db.String(200))
    title        = db.Column(db.String(120))
    revenue      = db.Column(db.String(50))
    employees    = db.Column(db.String(50))
    industry     = db.Column(db.String(100))
    package      = db.Column(db.String(100))
    message      = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def send_lead_notification(lead):
    """Email the lead details to the configured inbox. Fails silently if mail is not configured."""
    if not app.config['MAIL_USERNAME']:
        return
    try:
        recipient = os.environ.get('NOTIFICATION_EMAIL', app.config['MAIL_USERNAME'])
        msg = Message(
            subject=f"New Consultation Request — {lead.name} ({lead.company or 'No company'})",
            recipients=[recipient],
            body=f"""New consultation request received via the Aurelian Group website.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTACT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name:             {lead.name}
Email:            {lead.email}
Organization:     {lead.company or '—'}
Role:             {lead.title or '—'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMPANY PROFILE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Annual Revenue:   {lead.revenue or '—'}
Headcount:        {lead.employees or '—'}
Sector:           {lead.industry or '—'}
Area of Interest: {lead.package or '—'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MESSAGE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{lead.message}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Submitted: {lead.submitted_at.strftime('%B %d, %Y at %I:%M %p UTC')}
View all leads: /admin/leads
"""
        )
        mail.send(msg)
    except Exception:
        pass  # Don't break the user experience if mail fails


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────
# PUBLIC ROUTES
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name    = request.form.get('name', '').strip()
        email   = request.form.get('email', '').strip()
        company = request.form.get('company', '').strip()
        title   = request.form.get('title', '').strip()
        revenue = request.form.get('revenue', '').strip()
        employees = request.form.get('employees', '').strip()
        industry  = request.form.get('industry', '').strip()
        package   = request.form.get('package', '').strip()
        message   = request.form.get('message', '').strip()

        if name and email and message:
            lead = Lead(
                name=name, email=email, company=company, title=title,
                revenue=revenue, employees=employees, industry=industry,
                package=package, message=message
            )
            db.session.add(lead)
            db.session.commit()
            send_lead_notification(lead)
            flash('Your submission has been received. We will respond within 24 business hours.', 'success')
        else:
            flash('Please complete all required fields before submitting.', 'error')
        return redirect(url_for('contact'))
    return render_template('contact.html')


# ─────────────────────────────────────────────
# ADMIN ROUTES
# ─────────────────────────────────────────────

@app.route('/admin')
def admin_login():
    if session.get('admin_logged_in'):
        return redirect(url_for('admin_leads'))
    return render_template('admin/login.html')

@app.route('/admin/login', methods=['POST'])
def admin_login_post():
    password = request.form.get('password', '')
    admin_pw = os.environ.get('ADMIN_PASSWORD', 'aurelian-admin-2024')
    if password == admin_pw:
        session['admin_logged_in'] = True
        return redirect(url_for('admin_leads'))
    flash('Incorrect password.', 'error')
    return redirect(url_for('admin_login'))

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/leads')
@admin_required
def admin_leads():
    leads = Lead.query.order_by(Lead.submitted_at.desc()).all()
    return render_template('admin/leads.html', leads=leads)


# ─────────────────────────────────────────────
# INIT
# ─────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5001)
