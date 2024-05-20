import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, render_template, flash, request
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy.exc import SQLAlchemyError
from wtforms import StringField, SubmitField, EmailField
from wtforms.validators import DataRequired

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:N1pun$@localhost/users'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

db = SQLAlchemy(app)
migrate = Migrate(app, db)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False, unique=True)
    favorite_color = db.Column(db.String(50))
    date_added = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f'<Name {self.name}>'


class NameForm(FlaskForm):
    name = StringField('Enter your name', validators=[DataRequired()])
    submit = SubmitField('Submit')


class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    favorite_color = StringField('Favorite Color')
    submit = SubmitField('Submit')


@app.route('/')
def index():
    favorite_pizza = ['Pepperoni', 'Cheese', 'Mushrooms']
    return render_template('index.html', favorite_pizza=favorite_pizza)


@app.route('/user/<name>')
def user(name):
    return render_template('user.html', name=name)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404


@app.errorhandler(500)
def special_exception_handler(error):
    return render_template('500.html'), 500


@app.route('/name-form', methods=['GET', 'POST'])
def name_form():
    name = None
    form = NameForm()
    if form.validate_on_submit():
        name = form.name.data
        form.name.data = ''
        flash('Form submitted successfully!')
    return render_template('name_form.html', name=name, form=form)


@app.route('/users', methods=['GET', 'POST'])
def user_form():
    name = None
    form = UserForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user is None:
            new_user = User(name=form.name.data, email=form.email.data,
                            favorite_color=form.favorite_color.data)
            db.session.add(new_user)
            db.session.commit()
        name = form.name.data
        form.name.data = ''
        form.email.data = ''
        form.favorite_color.data = ''
        flash('User added successfully!')
    users = User.query.order_by(User.date_added)
    return render_template('user_form.html', name=name, form=form, users=users)


@app.route('/update/<int:id>', methods=['GET', 'POST'])
def update_user(id):
    form = UserForm()
    user_to_update = User.query.get_or_404(id)

    if request.method == 'POST':
        user_to_update.name = request.form['name']
        user_to_update.email = request.form['email']
        user_to_update.favorite_color = request.form['favorite_color']
        try:
            db.session.commit()
            flash('User updated successfully!')
            return render_template('update.html', form=form, user_to_update=user_to_update)
        except SQLAlchemyError:
            flash('Database error, try again!')
            return render_template('update.html', form=form, user_to_update=user_to_update)
    else:
        return render_template('update.html', form=form, user_to_update=user_to_update)
