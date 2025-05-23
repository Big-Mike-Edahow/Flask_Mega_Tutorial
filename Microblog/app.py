# app.py
# My version of the Flask Mega Tutorial Microblog

from datetime import datetime, timezone
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.sql import func
from flask_login import UserMixin, LoginManager, login_required, login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from urllib.parse import urlsplit
from forms import LoginForm, RegistrationForm, EditProfileForm, PostForm, CommentForm

app = Flask(__name__)

app.config["SECRET_KEY"] = "My simple version of this app."
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy()
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True)
    password_hash = db.Column(db.String(100))
    email = db.Column(db.String(100))
    posts = db.relationship("Post", backref="user", lazy="dynamic")
    created = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp())
    nickname = db.Column(db.String(255))
    about = db.Column(db.Text())
    visited = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp())

    def __repr__(self):
        return "<User {}>".format(self.username)


class Post(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    author = db.Column(db.String(50))
    title = db.Column(db.String(255))
    body = db.Column(db.Text())
    created = db.Column(db.DateTime(timezone=True), server_default=db.func.current_timestamp())
    user_id = db.Column(db.Integer(), db.ForeignKey("user.id"), index=True)
    comments = db.relationship("Comment", backref="post", lazy="dynamic")

    def __repr__(self):
        return "<Post '{}'>".format(self.title)


class Comment(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    author = db.Column(db.String(255))
    comment = db.Column(db.Text())
    created = db.Column(
        db.DateTime(timezone=True), server_default=db.func.current_timestamp()
    )
    post_id = db.Column(db.Integer(), db.ForeignKey("post.id"), index=True)

    def __repr__(self):
        return "<Comment '{}'>".format(self.comment[:15])


# Create Database with App Context.
def createDB():
    with app.app_context():
        db.create_all()


# Handle file not found errors.
@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404


# Executed before any view function is called.
@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.visited = datetime.now(timezone.utc)
        db.session.commit()


@app.route("/")
def index():
    posts = Post.query.all()

    return render_template("index.html", title="Home", posts=posts)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        flash("You are already logged in.")
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        remember_me = form.remember_me.data
        user = User.query.filter_by(username=username).first()
        if user is None or not check_password_hash(user.password_hash, password):
            flash("Invalid username or password.")
            return redirect(url_for("login"))
        else:
            login_user(user, remember=remember_me)
            flash("You have been logged in successfully.")
            next_page = request.args.get("next")
            if not next_page or urlsplit(next_page).netloc != "":
                next_page = url_for("index")
            return redirect(next_page)
    return render_template("login.html", title="Login", form=form)


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        flash("You are already logged in.")
        return redirect(url_for("index"))
    form = RegistrationForm()
    if form.validate_on_submit():
        username = form.username.data
        email = form.email.data
        user = User.query.filter_by(username=username).first()
        if user:
            flash("Username already exists!")
            return redirect(url_for("register"))
        else:
            hashed_password = generate_password_hash(form.password.data)
            new_user = User(
                username=username, password_hash=hashed_password, email=email
            )
            db.session.add(new_user)
            db.session.commit()
            flash("Congratulations, you are now a registered user!")
            return redirect(url_for("login"))
    return render_template("register.html", title="Register", form=form)


@app.route("/create", methods=("GET", "POST"))
@login_required
def create():
    form = PostForm()
    if request.method == "GET":
        return render_template("create.html", title="Create", form=form)
    elif request.method == "POST":
        if form.validate_on_submit():
            new_post = Post()
            new_post.user_id = current_user.id
            new_post.title = form.title.data
            new_post.body = form.body.data
            new_post.author = current_user.username

            db.session.add(new_post)
            db.session.commit()
            return redirect(url_for("index"))
        else:
            return render_template("create.html", title="Create", form=form)


@app.route("/post/<int:post_id>", methods=("GET", "POST"))
def post(post_id):
    form = CommentForm()
    if form.validate_on_submit():
        new_comment = Comment()
        new_comment.author = current_user.username
        new_comment.comment = form.comment.data
        new_comment.post_id = post_id
        try:
            db.session.add(new_comment)
            db.session.commit()
        except Exception as e:
            flash("Error adding your comment: %s" % str(e), "error")
            db.session.rollback()
        else:
            flash("Comment added", "info")
        return redirect(url_for("post", title="View", post_id=post_id))

    post = Post.query.get_or_404(post_id)
    comments = post.comments.order_by(Comment.created.desc()).all()

    return render_template(
        "post.html", post=post, title="View Post", comments=comments, form=form
    )


@app.route("/edit_post/<int:id>", methods=["GET", "POST"])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    # Only the owner of the post can edit it.
    if current_user.id == post.user.id:
        form = PostForm()
        if form.validate_on_submit():
            post.title = form.title.data
            post.body = form.body.data
            db.session.merge(post)
            db.session.commit()
            return redirect(url_for("post", post_id=post.id))
        form.title.data = post.title
        form.body.data = post.body
        return render_template(
            "edit_post.html", title="Edit Post", form=form, post=post
        )
    else:
        flash("You are not the owner of this post.")
        return redirect(url_for("index"))


@app.route("/profile/<string:username>")
@login_required
def profile(username):
    user = User.query.filter_by(username=username).first()
    posts = user.posts.order_by(Post.created.desc()).all()
    return render_template("profile.html", title="User Profile", user=user, posts=posts)


@app.route("/edit_profile", methods=["GET", "POST"])
@login_required
def edit_profile():
    form = EditProfileForm()
    if request.method == "GET":
        form.nickname.data = current_user.nickname
        form.about.data = current_user.about
        return render_template("edit_profile.html", title="Edit Profile", form=form)
    elif request.method == "POST":
        if form.validate_on_submit():
            current_user.nickname = form.nickname.data
            current_user.about = form.about.data
            db.session.commit()
            flash("Your changes have been saved.")
            return redirect(url_for("profile", username=current_user.username))

        return render_template("edit_profile.html", title="Edit Profile", form=form)


@app.route("/delete/<int:id>")
@login_required
def delete(id):
    post = Post.query.get_or_404(id)
    # The post can only be deleted by it's owner.
    if current_user.id == post.user.id:
        db.session.delete(post)
        db.session.commit()
        flash("Post deleted successfully.")
        return redirect(url_for("index"))
    else:
        flash("You are not the owner of this post.")
        return redirect(url_for("index"))


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.")
    return redirect(url_for("login"))


@app.route("/about")
def about():
    return render_template("about.html", title="About")


if __name__ == "__main__":
    createDB()
    app.run(debug=True, port=8080)
