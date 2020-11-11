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
    classes = db.relationship('Course', secondary=subs, backref=db.backref('students_of_class', lazy='dynamic'))
    
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
    
    def __repr__(self):
        return f"Experiment('{self.name}','{self.owner_id}')"
    
    
class Setup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    period_of_res = db.Column(db.Integer, nullable=False)
    max_res_for_week = db.Column(db.Integer, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('experiment.id'), nullable=False)
    reservations = db.relationship('Reservation', backref='owner', lazy='dynamic')
    
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
        setup = Setup.query.filter_by(id=self.owner_id).first().name
        port = self.owner_id + 8800
        self.bash_file(token, setup, port)
        duration = int(duration)
        end_time = start_time + timedelta(minutes=duration)
        left = end_time - datetime.now()
        proc = subprocess.Popen(['gnome-terminal', '--disable-factory', '--', 'bash', '{}.sh'.format(setup)], preexec_fn=os.setpgrp)
        print('New student enviroment ready!')
        time.sleep(int(left.seconds)-30)
        print('Closing')
        os.killpg(proc.pid, signal.SIGINT)
        print('Closed')
    
    @staticmethod
    def bash_file(token, setup ,port):
        ip_adress = ip_find()
        text = []
        text.append('#!/bin/bash\n')
        text.append('\n')
        text.append('sudo su - {} <<EOF\n'.format(setup))
        text.append("jupyter notebook --no-browser --NotebookApp.token='' --NotebookApp.password={0} --ip {1} --port {2} --NotebookApp.terminals_enabled=False\n".format(token,ip_adress,port))
        text.append('EOF\n')
        with open('{}.sh'.format(setup),'w') as f:
            f.writelines(text)
      
    def __repr__(self):
        return f"Reservation('{self.res_date}','{self.owner_id}','{self.user_id}')"
