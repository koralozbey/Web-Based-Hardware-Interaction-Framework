from flask import redirect, render_template, request, url_for, flash, abort
from flask_server import app, db, bcrypt
from flask_server.forms import RegistrationForm, LoginForm
from flask_server.models import User, Reservation, Course, Experiment, Setup
from flask_server.functions import ip_find
from flask_login import login_user, current_user, logout_user, login_required
from datetime import timedelta,datetime,date
from datetime import time as dtime
import time
import threading
from notebook.auth import passwd


@app.route('/')
@app.route('/home')
def home():
    return render_template("home.html")
    
@app.route('/main_menu')
@login_required
def main_menu():
    return render_template("main_menu.html")
    
@app.route('/jupyternotebook')
@login_required
def jupyternotebook():
    ip_adress = ip_find()
    current_reservations = []
    now = datetime.now()
    for res in current_user.reservations.all():
        start = res.res_date
        end = start + timedelta(minutes=res.owner.period_of_res)
        if start < now and now < end:
            current_reservations.append(res)
    return render_template("jup_servers.html", current_reservations=current_reservations, ip_adress=ip_adress)

@app.route('/admin_panel')
@login_required
def admin_panel():
    if not current_user.is_admin:
        abort(401)
    return render_template("admin_panel.html")

@app.route('/jup_server_starter/<int:res_id>')
@login_required
def jup_server_starter(res_id):
    res = Reservation.query.filter_by(id=res_id).first()
    if current_user.id == res.user_id and res.is_started == False:
        start = res.res_date
        end = start + timedelta(minutes=res.owner.period_of_res)
        now = datetime.now()
        if start < now and now < end:
            t = threading.Thread(target=res.se)
            t.daemon = True
            t.start()
            res.is_started = True
            db.session.commit()
            time.sleep(2)
            return redirect(url_for('jupyternotebook'))
    return redirect(url_for('main_menu'))

@app.route("/register", methods=['GET','POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main_menu'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        sha1 = passwd(form.password.data, algorithm='sha1')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password,password_sha1=sha1)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in.')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route("/login", methods=['GET','POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main_menu'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            return redirect(url_for('main_menu'))
        else:
            flash('Login Unseccessful. Please check email and password.')
    return render_template('login.html', form=form)
    
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))
    
@app.route("/choose_setup")
@login_required
def deneme():
    return render_template('choose_setup.html', courses=Course.query.all())
    
@app.route("/schedule", methods=["POST"])
@login_required
def deneme_sonuc():
    selected = request.form.get('choosen_setup')
    setup = Setup.query.filter_by(id=selected).first()
    return render_template('schedule.html', datetime=datetime, date=date, timedelta=timedelta, time=dtime, setup=setup)
    
@app.route("/successful_reservations", methods=["POST"])
@login_required
def successful_reservations():
    selected_reservations = request.form.getlist('check')
    setup_id = int(request.form.get('setup_ID'))
    now = datetime.now()
    made_reservations = []
    successful_reservations = []
    for res in Setup.query.filter_by(id=setup_id).first().reservations.all():
        if res.res_date > now:
            made_reservations.append(res.res_date)
    if selected_reservations != [] and setup_id != None and current_user.is_authenticated:
        for res in selected_reservations:
            target_time = datetime.strptime(res,"%Y-%m-%d %H:%M")
            if target_time not in made_reservations and target_time > now:
                res1 = Reservation(res_date=target_time, owner_id=setup_id, user_id=current_user.id)
                db.session.add(res1)
                db.session.commit()
                successful_reservations.append(res)
        return render_template('successful_reservations.html', successful_reservations=successful_reservations)
    return 'Error: No reservation or check your login!'
    
@app.route('/my_reservations')
@login_required
def my_reservations():
    now = datetime.now()
    return render_template('my_reservations.html', my_res=current_user.reservations.all(), now=now)

@app.route('/cancel_reservation', methods=["POST"])
@login_required
def cancel_reservation():
    selected_reservations = request.form.getlist('check')
    for res in selected_reservations:
        res2cancel = Reservation.query.filter_by(id=res).first()
        if res2cancel.user_id != current_user.id:
            return "Current user do not own this reservation!"
        db.session.delete(res2cancel)
        db.session.commit()
    return redirect(url_for('main_menu'))
