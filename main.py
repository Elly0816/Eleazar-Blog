from flask import Flask, render_template, redirect, url_for, flash, request, abort
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from forms import CreatePostForm, RegisterForm, LoginForm, CommentForm
from flask_gravatar import Gravatar
from functools import wraps
from sqlalchemy import Table, Column, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
import os


Base = declarative_base()


app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
ckeditor = CKEditor(app)
Bootstrap(app)
login_manager = LoginManager(app)

## CONNECT TO DB
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///blog.db'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///blog.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


# CONFIGURE TABLES

class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    # set a foreign key for this field, id from the users table
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # define the relationship with the users table
    author = relationship("User", back_populates="posts")
    img_url = db.Column(db.String(250), nullable=False)
    # define the relationship with the comments table
    comments = relationship("Comment", back_populates="parent_post")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    # set foreign keys
    post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    # define the relationships with the other tables
    parent_post = relationship("BlogPost", back_populates="comments")
    comment_author = relationship("User", back_populates="comments")
    text = db.Column(db.Text, nullable=False)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))
    # define the relationship with the blog_posts table
    posts = relationship("BlogPost", back_populates="author")
    # define the relationship with the comments table
    comments = relationship("Comment", back_populates="comment_author")


# db.create_all()


# Decorator function for checking if the logged in user is the admin
def admin_only(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if current_user.is_authenticated:
            return func(*args, **kwargs)
        else:
            return abort(401)
    return wrapper



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


@app.route('/')
def get_all_posts():
    posts = BlogPost.query.all()
    
    return render_template("index.html", all_posts=posts, current_user=current_user, year=date.today().year)


@app.route('/register', methods=["POST", "GET"])
def register():
    form = RegisterForm()
    
    if request.method == "POST":
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            flash('You have already registered with that email. Log in instead')
            return redirect(url_for('login'))
        else:
            new_user = User(email=email,
                             password=generate_password_hash(request.form.get('password'),
                                                             method='pbkdf2:sha256',
                                                             salt_length=5),
                             name=request.form.get('name')
                             )
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user, remember=True)
            return redirect(url_for('get_all_posts'))
    return render_template("register.html", form=form, current_user=current_user, year=date.today().year)


@app.route('/login', methods=["POST", "GET"])
def login():
    form = LoginForm()
    
    if request.method == "POST":
        user = User.query.filter_by(email=request.form.get('email')).first()
        if user:
            if check_password_hash(user.password, request.form.get('password')):
                login_user(user, remember=True)
                return redirect(url_for('get_all_posts'))
            else:
                flash('Password Incorrect! Please try again.')
                return redirect(url_for('login'))
        else:
            flash("This email does not exist! Please try again.")
            return redirect(url_for('login'))
    else:
        return render_template("login.html", form=form, current_user=current_user, year=date.today().year)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('get_all_posts'))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    form = CommentForm()
    
    comments = Comment.query.all()
    requested_post = BlogPost.query.get(post_id)
    if form.validate_on_submit():
        new_comment = Comment(text=request.form.get('comment'),
                              post_id=requested_post.id,
                              author_id=current_user.id)
        db.session.add(new_comment)
        db.session.commit()
        return redirect(url_for('show_post', post_id=requested_post.id))
    return render_template("post.html", post=requested_post, current_user=current_user, form=form, comments=comments, year=date.today().year)


@app.route("/about")
def about():
    
    return render_template("about.html", current_user=current_user, year=date.today().year)


@app.route("/contact")
def contact():
    
    return render_template("contact.html", current_user=current_user, year=date.today().year)


@app.route("/new-post", methods=["POST", "GET"])
@admin_only
def add_new_post():
    form = CreatePostForm()
    
    if form.validate_on_submit():
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            author=current_user,
            date=date.today().strftime("%B %d, %Y")
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts"))
    return render_template("make-post.html", form=form, current_user=current_user, year=date.today().year)


@app.route("/edit-post/<int:post_id>", methods=["POST", "GET"])
@admin_only
def edit_post(post_id):
    
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        body=post.body
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(url_for("show_post", post_id=post.id))

    return render_template("make-post.html", form=edit_form, current_user=current_user, year=date.today().year)


@app.route("/delete/<int:post_id>")
@admin_only
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for('get_all_posts'))


if __name__ == "__main__":
    app.run(debug=True)
