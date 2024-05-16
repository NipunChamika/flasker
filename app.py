import os
from flask import Flask, render_template
from dotenv import load_dotenv
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')


class Form(FlaskForm):
    name = StringField('Enter your name', validators=[DataRequired()])
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
    form = Form()
    if form.validate_on_submit():
        name = form.name.data
        form.name.data = ''
    return render_template('form.html', name=name, form=form)
