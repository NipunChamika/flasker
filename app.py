import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, flash, request, url_for
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import PasswordField, StringField, SubmitField, EmailField, TextAreaField
from wtforms.validators import DataRequired, EqualTo

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
    password_hash = db.Column(db.String(255), nullable=False)
    date_added = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc))

    @property
    def password(self):
        raise AttributeError('Password is not a readable attribute.')

    @password.setter
    def password(self, password):
        self.password = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password, password)

    def __repr__(self) -> str:
        return f'<Name {self.name}>'


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255))
    content = db.Column(db.Text)
    author = db.Column(db.String(255))
    slug = db.Column(db.String(255))
    date_posted = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc))


class NameForm(FlaskForm):
    name = StringField('Enter your name', validators=[DataRequired()])
    submit = SubmitField('Submit')


class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    favorite_color = StringField('Favorite Color')
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[
                                     DataRequired(), EqualTo('password', message='Passwords must match!')])
    submit = SubmitField('Submit')


class LoginForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')


class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    slug = StringField('Slug', validators=[DataRequired()])
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
def add_user():
    name = None
    form = UserForm()
    if form.validate_on_submit():
        existing_user = User.query.filter_by(email=form.email.data).first()
        if existing_user is None:
            hashed_password = generate_password_hash(form.password.data)
            new_user = User(name=form.name.data, email=form.email.data,
                            favorite_color=form.favorite_color.data, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
        name = form.name.data
        form.name.data = ''
        form.email.data = ''
        form.favorite_color.data = ''
        form.password = ''
        flash('User added successfully!')
    users = User.query.order_by(User.date_added)
    return render_template('add_user.html', name=name, form=form, users=users)


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
        return render_template('update.html', form=form, user_to_update=user_to_update, id=id)


@app.route('/delete/<int:id>')
def delete_user(id):
    user_to_delete = User.query.get_or_404(id)

    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('User deleted successfully!')
        return redirect(url_for('add_user'))
    except SQLAlchemyError:
        flash('Database error, try again!')
        return redirect(url_for('add_user'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    email = None
    password = None
    user = None
    logged_in = None
    form = LoginForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        form.email.data = ''
        form.password.data = ''

        user = User.query.filter_by(email=email).first()

        if user:
            logged_in = check_password_hash(user.password_hash, password)
        else:
            flash('Wrong email or password')

    return render_template('login.html', email=email, user=user, logged_in=logged_in, form=form)


@app.route('/add-post', methods=['GET', 'POST'])
def add_post():
    form = PostForm()

    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data,
                    author=form.author.data, slug=form.slug.data)

        form.title.data = ''
        form.content.data = ''
        form.author.data = ''
        form.slug.data = ''

        db.session.add(post)
        db.session.commit()
        flash('Post created successfully!')

    posts = Post.query.order_by(Post.date_posted)
    return render_template('add_post.html', title=form.title.data, form=form, posts=posts)


@app.route('/posts')
def posts():
    posts = Post.query.order_by(Post.date_posted)
    return render_template('posts.html', posts=posts)
