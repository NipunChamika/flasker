import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from flask import Flask, redirect, render_template, flash, request, url_for
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from sqlalchemy import or_
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.security import generate_password_hash, check_password_hash
from wtforms import PasswordField, StringField, SubmitField, EmailField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, EqualTo

load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:N1pun$@localhost/users'
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'danger'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    username = db.Column(db.String(255), nullable=False, unique=True)
    email = db.Column(db.String(255), nullable=False, unique=True)
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


class UsernameValidator(object):
    def __init__(self, message=None):
        if not message:
            message = 'Username must not contain spaces.'
        self.message = message

    def __call__(self, form, field):
        if ' ' in field.data:
            raise ValidationError(self.message)


class NameForm(FlaskForm):
    name = StringField('Enter your name', validators=[DataRequired()])
    submit = SubmitField('Submit')


class UserForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    email = EmailField('Email', validators=[DataRequired()])
    username = StringField('Username', validators=[
                           DataRequired(), UsernameValidator()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[
                                     DataRequired(), EqualTo('password', message='Passwords must match!')])
    submit = SubmitField('Submit')


class PasswordForm(FlaskForm):
    email = EmailField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Submit')


class PostForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired()])
    content = TextAreaField('Content', validators=[DataRequired()])
    author = StringField('Author', validators=[DataRequired()])
    slug = StringField('Slug', validators=[DataRequired()])
    submit = SubmitField('Submit')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[
                           DataRequired(), UsernameValidator()])
    password = PasswordField('Password', validators=[DataRequired()])
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
        flash('Form submitted successfully!', 'success')
    return render_template('name_form.html', name=name, form=form)


@app.route('/users', methods=['GET', 'POST'])
def add_user():
    user_added = False
    form = UserForm()

    if form.validate_on_submit():
        existing_user = User.query.filter(or_(
            User.email == form.email.data, User.username == form.username.data.lower())).first()
        if existing_user is None:
            hashed_password = generate_password_hash(form.password.data)
            new_user = User(name=form.name.data, username=form.username.data.lower(),
                            email=form.email.data, password_hash=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            user_added = True
            flash('User added successfully!', 'success')
        else:
            if existing_user.username == form.username.data.lower():
                flash(
                    'Username already exists. Please choose a different username.', 'danger')
            elif existing_user.email == form.email.data:
                flash('Email already exists.', 'danger')

        form.name.data = ''
        form.username.data = ''
        form.email.data = ''
        form.password.data = ''
        form.confirm_password.data = ''
    users = User.query.order_by(User.date_added)
    return render_template('add_user.html', user_added=user_added, form=form, users=users)


@app.route('/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update_user(id):
    form = UserForm()
    user_to_update = User.query.get_or_404(id)

    if request.method == 'POST':
        user_to_update.name = request.form['name']
        user_to_update.username = request.form['username']
        user_to_update.email = request.form['email']
        try:
            db.session.commit()
            flash('User updated successfully!', 'success')
            return render_template('update.html', form=form, user_to_update=user_to_update)
        except SQLAlchemyError:
            flash('Database error, try again!', 'danger')
            return render_template('update.html', form=form, user_to_update=user_to_update)
    else:
        return render_template('update.html', form=form, user_to_update=user_to_update, id=id)


@app.route('/delete/<int:id>')
@login_required
def delete_user(id):
    user_to_delete = User.query.get_or_404(id)

    try:
        db.session.delete(user_to_delete)
        db.session.commit()
        flash('User deleted successfully!', 'success')
        return redirect(url_for('add_user'))
    except SQLAlchemyError:
        flash('Database error, try again!', 'danger')
        return redirect(url_for('add_user'))


@app.route('/test_pw', methods=['GET', 'POST'])
def test_pw():
    email = None
    password = None
    user = None
    logged_in = None
    form = PasswordForm()

    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        form.email.data = ''
        form.password.data = ''

        user = User.query.filter_by(email=email).first()

        if user:
            logged_in = check_password_hash(user.password_hash, password)
        else:
            flash('Wrong email or password', 'danger')

    return render_template('test_pw.html', email=email, user=user, logged_in=logged_in, form=form)


@app.route('/add-post', methods=['GET', 'POST'])
@login_required
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
        flash('Post created successfully!', 'success')

    posts = Post.query.order_by(Post.date_posted)
    return render_template('add_post.html', title=form.title.data, form=form, posts=posts)


@app.route('/posts')
def posts():
    posts = Post.query.order_by(Post.date_posted)
    return render_template('posts.html', posts=posts)


@app.route('/posts/<int:id>')
def post(id):
    post = Post.query.get_or_404(id)
    return render_template('post.html', post=post)


@app.route('/posts/update/<int:id>', methods=['GET', 'POST'])
@login_required
def update_post(id):
    form = PostForm()
    post = Post.query.get_or_404(id)

    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.author = form.author.data
        post.slug = form.slug.data

        db.session.add(post)
        db.session.commit()
        flash('Post updated successfully!', 'success')
        return redirect(url_for('post', id=post.id))

    form.title.data = post.title
    form.content.data = post.content
    form.author.data = post.author
    form.slug.data = post.slug
    return render_template('update_post.html', form=form)


@app.route('/posts/delete/<int:id>')
@login_required
def delete_post(id):
    post = Post.query.get_or_404(id)

    try:
        db.session.delete(post)
        db.session.commit()
        flash('Post deleted successfully!', 'success')
        return redirect(url_for('posts'))
    except SQLAlchemyError:
        flash('Database error, try again!', 'danger')
        return redirect(url_for('posts'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    user = None
    logged_in = None
    form = LoginForm()

    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        form.username.data = ''
        form.password.data = ''

        user = User.query.filter_by(username=username).first()

        if user:
            if check_password_hash(user.password_hash, password):
                login_user(user)
                return redirect(url_for('dashboard'))
            flash('Wrong username or password.', 'danger')
        else:
            flash('Wrong username or password.', 'danger')

    return render_template('login.html', form=form, logged_in=logged_in, user=user)


@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))
