# This script creates a sample database for test purpose

from flask_server import db
from flask_server.models import User, Course, Experiment, Material, Setup, Reservation
from flask_bcrypt import Bcrypt
from notebook.auth import passwd
import datetime


bcrypt = Bcrypt()

db.drop_all()
db.create_all()

'''
course1 = Course(name='ME220')
course2 = Course(name='ME461')
db.session.add(course1)
db.session.add(course2)
db.session.commit()

experiment1 = Experiment(name='lab1',owner_id=Course.query.filter_by(name='ME461').first().id)
experiment2 = Experiment(name='training1',owner_id=Course.query.filter_by(name='ME220').first().id)
db.session.add(experiment1)
db.session.add(experiment2)
db.session.commit()

#Setup model changed
setup1 = Setup(name='setup1',period_of_res=5,max_res_for_week=3,owner_id=1)
setup2 = Setup(name='setup3',period_of_res=60,max_res_for_week=3,owner_id=2)
db.session.add(setup1)
db.session.add(setup2)
db.session.commit()

passs1 = 'koral231'
hashed_password1 = bcrypt.generate_password_hash(passs1).decode('utf-8')
sha1_1 = passwd(passs1, algorithm='sha1')
user1 = User(username='Koral Ozbey', email='koral@koral.com', password=hashed_password1,password_sha1=sha1_1)
db.session.add(user1)
'''
passs2 = 'admin231'
hashed_password2 = bcrypt.generate_password_hash(passs2).decode('utf-8')
sha1_2 = passwd(passs2, algorithm='sha1')
user2 = User(username='Admin', email='admin@koral.com', password=hashed_password2,password_sha1=sha1_2,is_admin=True)
db.session.add(user2)
db.session.commit()


