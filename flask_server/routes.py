from flask import redirect, render_template, request, url_for, flash, abort, send_from_directory
from flask_server import app, db, bcrypt
from flask_server.forms import RegistrationForm, LoginForm
from flask_server.models import User, Reservation, Course, Experiment, Material, Setup
from flask_server.functions import ip_find, allowed_file, tty_ports, setup_infos
from flask_login import login_user, current_user, logout_user, login_required
from datetime import timedelta,datetime,date
from datetime import time as dtime
import time
import threading
from notebook.auth import passwd
import os #To save experiment files
from werkzeug.utils import secure_filename #To prevent malicious filenames


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
        end = start + timedelta(minutes=res.owner.period_of_res-1)
        now = datetime.now()
        if start < now and now < end:
            t = threading.Thread(target=res.se)
            t.daemon = True
            t.start()
            res.is_started = True
            db.session.commit()
            time.sleep(7)
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
        flash('Your account has been created! You are now able to log in.','success')
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
def choose_setup():
    return render_template('choose_setup.html', courses=Course.query.all())
    
@app.route("/schedule", methods=["POST"])
@login_required
def schedule():
    selected = request.form.get('chosen_setup')
    if selected == None:
        flash('Please choose a setup.')
        return redirect(url_for('choose_setup',  courses=Course.query.all()))
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
    return render_template('my_reservations.html', my_res=current_user.reservations.all(), now=now, label='My')

@app.route('/cancel_reservation', methods=["POST"])
@login_required
def cancel_reservation():
    selected_reservations = request.form.getlist('check')
    for res in selected_reservations:
        res2cancel = Reservation.query.filter_by(id=res).first()
        if res2cancel.user_id == current_user.id or current_user.is_admin:
            db.session.delete(res2cancel)
            db.session.commit()
        else:
            now = datetime.now()
            flash("Current user do not own this reservation!")
            return redirect(url_for('my_reservations', my_res=current_user.reservations.all(), now=now, label='My'))
    return redirect(url_for('main_menu'))
    
@app.route('/admin_panel/subcategory2control')
@login_required
def subcategory2control():
    if not current_user.is_admin:
        abort(401)
    return render_template("subcategory2control.html", courses=Course.query.all(), users=User.query.all())
    
@app.route('/admin_panel/subcategory2control/reservation2control', methods=["POST"])
@login_required
def reservation2control():
    if not current_user.is_admin:
        abort(401)
    selected = request.form.get('chosen_subcategory')
    if selected == None:
        flash('Please choose a subcategory.')
        return redirect(url_for('subcategory2control',  courses=Course.query.all(), users=User.query.all()))
    selected = selected.split('=')
    if len(selected) != 2:
        flash("Error: Something went wrong. Contact administrator")
        return redirect(url_for('subcategory2control',  courses=Course.query.all(), users=User.query.all()))
    selected_class = selected[0]
    selected_id = selected[1]
    res2inspect = []
    
    if selected_class == 'course':
        label = Course.query.filter_by(id=selected_id).first().name
        for exp in Course.query.filter_by(id=selected_id).first().experiments.all():
            for stp in exp.setups.all():
                for res in stp.reservations.all():
                    res2inspect.append(res)
    elif selected_class == 'experiment':
        label = Experiment.query.filter_by(id=selected_id).first().name
        for stp in Experiment.query.filter_by(id=selected_id).first().setups.all():
            for res in stp.reservations.all():
                res2inspect.append(res)
    elif selected_class == 'setup':
        label = Setup.query.filter_by(id=selected_id).first().name
        for res in Setup.query.filter_by(id=selected_id).first().reservations.all():
            res2inspect.append(res)
    elif selected_class == 'person':
        label = User.query.filter_by(id=selected_id).first().username
        res2inspect = User.query.filter_by(id=selected_id).first().reservations.all()
    
    now = datetime.now()
    return render_template('my_reservations.html', my_res=res2inspect, now=now, label=label)

@app.route('/admin_panel/add_new', methods=["POST","GET"])
@login_required
def add_new():
    if not current_user.is_admin:
        abort(401)
    ports = tty_ports()
    if request.method == "GET":
        return render_template('admin_add_new.html', courses=Course.query.all(), ports=ports)
        
    if request.method == "POST":#use just else?
        if request.form.get('submit') == "Create Course":
            course_name = request.form.get('course_name')#max len=50 in model
            if course_name.strip() == '':
                flash('Course name cannot be empty.')
                return redirect(url_for('add_new'))
            if Course.query.filter_by(name=course_name).all():
                flash('This course name exists. Try with new name.')
                return redirect(url_for('add_new'))
            #Create course
            course2create = Course(name=course_name)
            db.session.add(course2create)
            db.session.commit()
            flash(f'Course {course_name} has been created!','success')
            return redirect(url_for('add_new'))
            
        elif request.form.get('submit') == "Create Experiment":
            course_id = request.form.get('choosen_course')
            if not course_id:
                flash('Please choose a course.')
                return redirect(url_for('add_new'))
            experiment_name = request.form.get('experiment_name')#max len=50 in model
            if experiment_name.strip() == '':
                flash('Experiment name cannot be empty.')
                return redirect(url_for('add_new'))
            #Create experiment
            for exp in Course.query.filter_by(id=course_id).first().experiments:
                if exp.name == experiment_name:
                    flash('This experiment name exists in same course. Try with new name.')
                    return redirect(url_for('add_new'))
            experiment2create = Experiment(name=experiment_name,owner_id=course_id)
            db.session.add(experiment2create)
            db.session.commit()
            flash(f'Experiment {experiment_name} for {Course.query.filter_by(id=course_id).first().name} has been created!','success')
            return redirect(url_for('add_new'))
            
        elif request.form.get('submit') == "Upload Material":
            if 'file' not in request.files:
                flash('No file part')
                return redirect(url_for('add_new'))
            file2upload = request.files.get('file')
            experiment_id = request.form.get('choosen_experiment')
            if file2upload.filename == '':
                flash('No selected file')
                return redirect(url_for('add_new'))
            if file2upload and allowed_file(file2upload.filename):
                #Create file object and upload file
                filename = secure_filename(file2upload.filename)
                if Material.query.filter_by(name = filename).all():
                    flash('A file exist with same name!')
                    return redirect(url_for('add_new'))
                else:
                    file2upload.save(os.path.join(os.getcwd() + app.config['UPLOAD_FOLDER'], filename))
                    material2create = Material(name=filename,owner_id=experiment_id)
                    db.session.add(material2create)
                    db.session.commit()
                    flash(f'Material {filename} for {Experiment.query.filter_by(id=experiment_id).first().name} has been uploaded!','success')
                    return redirect(url_for('add_new'))
            else:
                flash('Material extension not allowed!')
                return redirect(url_for('add_new'))
            
        #setup handling
        elif request.form.get('submit') == "Create Setup":
            experiment_id = request.form.get('choosen_experiment')
            setup_name = request.form.get('setup_name')#max len=50 in model
            period_of_res = request.form.get('period_of_res')
            max_res_for_week = request.form.get('max_res_for_week')
            choosen_port = request.form.get('choosen_port')
            if setup_name.strip() == '':
                flash('Setup name cannot be empty.')
                return redirect(url_for('add_new'))
            for stp in Experiment.query.filter_by(id=experiment_id).first().setups:
                if stp.name == setup_name:
                    flash('This setup name exists in same experiment. Try with new name.')
                    return redirect(url_for('add_new'))
            #Create setup
            return redirect(url_for('setup_confirmation',
                                    experiment_id=experiment_id,
                                    setup_name=setup_name,
                                    period_of_res=period_of_res,
                                    max_res_for_week=max_res_for_week,
                                    choosen_port=choosen_port))

@app.route('/admin_panel/setup_confirm')
@login_required
def setup_confirmation():
    if not current_user.is_admin:
        abort(401)
    ports = tty_ports()
    experiment_id = request.args.get('experiment_id')
    setup_name = request.args.get('setup_name')#max len=50 in model
    period_of_res = request.args.get('period_of_res')
    max_res_for_week = request.args.get('max_res_for_week')
    choosen_port = request.args.get('choosen_port')
    if choosen_port:
        product_id,product_serial = setup_infos(choosen_port)
    else:
        flash("No port has chosen!")
        return redirect(url_for('add_new'))
    if product_id == -1 or product_serial == -1:
        flash("Product ID or Product serial no not found. Create setup unsuccessful!")
        return redirect(url_for('add_new'))
    for stp in Setup.query.all():
        if stp.product_serial == product_serial:
            flash("Another setup exists with same product serial. Create setup unsuccessful!")
            return redirect(url_for('add_new'))
    setup2create = Setup(name=setup_name,period_of_res=period_of_res,max_res_for_week=max_res_for_week,product_id=product_id,product_serial=product_serial,owner_id=experiment_id)
    db.session.add(setup2create)
    db.session.commit()
    setup2create = Setup.query.filter_by(product_serial=product_serial).first()
    setup2create.setup_user_creator()
    flash(f"Setup {setup_name} for {Experiment.query.filter_by(id=experiment_id).first().name} successful!",'success')
    flash('Reboot the system to enable USB port rules.')
    #Hide Code cell should be enabled for new user
    return redirect(url_for('add_new'))
    

@app.route('/admin_panel/download_materials', methods=["POST","GET"])
@login_required
def download_materials():
    if not current_user.is_admin:
        abort(401)
    if request.method == "GET":
        return render_template('download_materials.html', courses=Course.query.all(), materials=[])
        
    elif request.method == "POST":
        if request.form.get('submit') == "Choose Course":
            experiment_id = request.form.get('choosen_experiment')
            return render_template('download_materials.html', courses=Course.query.all(), materials=Experiment.query.filter_by(id=experiment_id).first().materials)
        elif request.form.get('submit') == "Download":
            file2download = request.form.get('choosen_material')
            return redirect(url_for('download_file', filename=Material.query.filter_by(id=file2download).first().name))
    
    
@app.route('/download/<filename>')
@login_required
def download_file(filename):
    if not current_user.is_admin:
        abort(401)
    return send_from_directory(os.getcwd() + app.config['UPLOAD_FOLDER'], filename)

@app.route('/admin_panel/delete_model', methods=["POST","GET"])
@login_required
def delete_model():
    if not current_user.is_admin:
        abort(401)
    if request.method == "GET":
        return render_template('delete_model.html', courses=Course.query.all())
        
    if request.method == "POST":
        action2take = request.form.get('submit')
        if action2take == "Delete Course":
            course_id = request.form.get('chosen_course')
            course2delete = Course.query.filter_by(id=course_id).first()
            if course2delete.experiments.all():
                flash(f'{course2delete.name} contains experiment! Please, first delete it.')
                return redirect(url_for('delete_model'))
            db.session.delete(course2delete)
            db.session.commit()
            flash(f'{course2delete.name} has been deleted!','success')
            return redirect(url_for('delete_model'))
            
        elif action2take == "Delete Experiment":
            experiment_id = request.form.get('chosen_experiment')
            experiment2delete = Experiment.query.filter_by(id=experiment_id).first()
            if experiment2delete.setups.all() or experiment2delete.materials.all():
                flash(f'{experiment2delete.name} contains setup or material! Please, first delete them.')
                return redirect(url_for('delete_model'))
            db.session.delete(experiment2delete)
            db.session.commit()
            flash(f'{experiment2delete.name} has been deleted!','success')
            return redirect(url_for('delete_model'))
            
        elif action2take == "Delete Material":
            material_id = request.form.get('chosen_material')
            material2delete = Material.query.filter_by(id=material_id).first()
            os.system(f"rm {app.config['UPLOAD_FOLDER'][1:]+'/'+material2delete.name}")
            db.session.delete(material2delete)
            db.session.commit()
            flash(f'{material2delete.name} has been deleted!','success')
            return redirect(url_for('delete_model'))
            
        elif action2take == "Delete Setup":
            setup_id = request.form.get('chosen_setup')
            setup2delete = Setup.query.filter_by(id=setup_id).first()
            for res in setup2delete.reservations.all():
                db.session.delete(res)
                db.session.commit()
            setup2delete.setup_user_delete()
            db.session.delete(setup2delete)
            db.session.commit()
            flash(f'{setup2delete.name} has been deleted!','success')
            return redirect(url_for('delete_model'))
