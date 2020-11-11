from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager


app = Flask(__name__)
app.config['SECRET_KEY'] = '1c02a663cd0b93333059785fe70d39ca'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db?check_same_thread=False'
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

from flask_server import routes

