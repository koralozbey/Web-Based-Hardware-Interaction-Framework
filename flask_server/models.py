from datetime import datetime, timedelta
from flask_server import db, login_manager
from flask_server.functions import ip_find
from flask_login import UserMixin
import os
import signal
import subprocess
import time


subs = db.Table('subs',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id')),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id')),
)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    password_sha1 = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean(), nullable=False, default=False)
    reservations = db.relationship('Reservation', backref='owner_student', lazy='dynamic')
    classes = db.relationship('Course', secondary=subs, backref=db.backref('students_of_class', lazy='dynamic'))#Currently not in use
    
    def __repr__(self):
        return f"User('{self.username}','{self.email}')"
        

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    experiments = db.relationship('Experiment', backref='owner', lazy='dynamic')
    
    def __repr__(self):
        return f"Course('{self.name}')"
    
    
class Experiment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    setups = db.relationship('Setup', backref='owner', lazy='dynamic')
    materials = db.relationship('Material', backref='owner', lazy='dynamic')
    # Add files with relationship - ADDED
    
    def __repr__(self):
        return f"Experiment('{self.name}','{self.owner_id}')"
    
class Material(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('experiment.id'), nullable=False)
    
    def __repr__(self):
        return f"Material('{self.name}','{self.owner_id}')"
    
class Setup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    period_of_res = db.Column(db.Integer, nullable=False)
    max_res_for_week = db.Column(db.Integer, nullable=False)#Currently not in use
    product_id = db.Column(db.String(150), nullable=False)
    product_serial = db.Column(db.String(150), unique=True, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('experiment.id'), nullable=False)
    reservations = db.relationship('Reservation', backref='owner', lazy='dynamic')
    
    def setup_user_creator(self):
        os.system(f'sudo useradd -m -d /home/setup{self.id} -s /bin/bash setup{self.id}')
        os.system(f'sudo chown -R setup{self.id} /home/setup{self.id}')
        os.system(f'sudo chmod -R 750 /home/setup{self.id}')
        self.rule_file(self.product_id,self.product_serial,self.id)
        os.system(f'sudo cp 99-setup{self.id}.rules /etc/udev/rules.d/')
        os.remove(f'99-setup{self.id}.rules')
        
    def setup_user_delete(self):
        os.system(f'sudo rm /etc/udev/rules.d/99-setup{self.id}.rules')
        os.system(f'sudo userdel -r setup{self.id}')
        
    @staticmethod
    def rule_file(product_id,product_serial,setup_id):
        text = []
        text.append(f'SUBSYSTEM=="tty", ATTRS{{idProduct}}=="{product_id}", ATTRS{{serial}}=="{product_serial}", ACTION=="add", RUN+="/bin/setfacl -m u:setup{setup_id}:rw- /dev/$name"')
        with open(f'99-setup{setup_id}.rules','w') as f:
            f.writelines(text)
    
    def __repr__(self):
        return f"Setup('{self.name}','{self.period_of_res}','{self.max_res_for_week}','{self.owner_id}')"
    

class Reservation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    res_date = db.Column(db.DateTime, nullable=False)
    res_moment = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    is_started = db.Column(db.Boolean(), nullable=False, default=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('setup.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def se(self): # se:Student Enviroment Starter
        start_time = self.res_date
        duration = Setup.query.filter_by(id=self.owner_id).first().period_of_res
        token = User.query.filter_by(id=self.user_id).first().password_sha1
        setup = Setup.query.filter_by(id=self.owner_id).first()
        port = self.owner_id + 8800
        self.bash_file(token, setup.id, port)
        duration = int(duration)
        end_time = start_time + timedelta(minutes=duration)
        left = end_time - datetime.now()
        proc = subprocess.Popen(['gnome-terminal', '--disable-factory', '--', 'bash', 'setup{}.sh'.format(setup.id)], preexec_fn=os.setpgrp)
        o_e_id = Setup.query.filter_by(id=self.owner_id).first().owner_id
        self.cp_materials(o_e_id,setup.id)
        print(f'New student enviroment ready for {setup.name}!')
        time.sleep(int(left.seconds)-10)
        print(f'{setup.name} is closing')
        os.killpg(proc.pid, signal.SIGINT)
        os.remove(f'setup{setup.id}.sh')
        print(f'{setup.name} has closed')
    
    @staticmethod
    def bash_file(token, setup_id ,port):
        ip_adress = ip_find()
        text = []
        text.append('#!/bin/bash\n')
        text.append('\n')
        text.append('sudo su - setup{} <<EOF\n'.format(setup_id))
        text.append('rm -rf *\n')
        text.append("jupyter notebook --no-browser --NotebookApp.token='' --NotebookApp.password={0} --ip {1} --port {2} --NotebookApp.terminals_enabled=False\n".format(token,ip_adress,port))
        text.append('EOF\n')
        with open('setup{}.sh'.format(setup_id),'w') as f:
            f.writelines(text)
    
    @staticmethod
    def cp_materials(o_e_id,setup_id):
        time.sleep(3)#If no delay put, materials delete in the subprocess
        mtrls = Experiment.query.filter_by(id=o_e_id).first().materials.all()
        for m in mtrls:
            os.system(f'sudo cp uploads/{m.name} /home/setup{setup_id}/')
        return

        
    def __repr__(self):
        return f"Reservation('{self.res_date}','{self.owner_id}','{self.user_id}')"
