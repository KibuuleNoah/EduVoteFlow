# imports
from flask import (
    render_template,
    request,
    Blueprint,
    redirect,
    url_for,
    current_app,
    flash,
)
from werkzeug.utils import secure_filename
from VoteFlow.users.forms import SchoolLogin, SchoolRegister

# from VoteFlow.models import SchoolUser, Poll
from VoteFlow import db  # , bcrypt
from VoteFlow.models import School
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user

# from .utils import img2svg

# Register this Page as a Blueprint
users = Blueprint("users", __name__)

host = "http://localhost:5000/"

# All Routes


@users.route("/login", methods=["GET", "POST"])
def school_login():
    form = SchoolLogin()
    if form.validate_on_submit():
        school_abbr = request.form["school_abbr"]
        school = School.query.filter_by(
            admin_username=form.admin_username.data, school_abbr=school_abbr
        ).first()

        if not school:
            flash(
                "School Doesn't Exist,Check Well the Admin User Name or School Abbr",
                "danger",
            )
        elif not check_password_hash(school.password, form.password.data):
            flash(
                f"Password for School {school_abbr} is Wrong!!",
                "danger",
            )

        else:
            login_user(school, remember=form.remember.data)
            return redirect(
                url_for("polls.poll_screen", school_abbr=school.school_abbr)
            )

    return render_template("login.html", title="Login - VoteFlow", form=form, host=host)


@users.route("/logout")
def school_logout():
    logout_user()
    return redirect(url_for("users.school_login"))


@users.route("/register", methods=["GET", "POST"])
def school_register():
    form = SchoolRegister()
    if form.validate_on_submit():
        # Get Form Data
        school_name = request.form["school_name"]
        school_abbr = request.form["school_abbr"]
        admin_username = request.form["admin_username"]
        password = request.form["password"]
        email = request.form["email"]
        school_logo = request.files["school_logo"]

        # Save Logo
        import os.path

        logo_ext = os.path.splitext(secure_filename(school_logo.filename))[
            1
        ]  # Get Extension

        logofilename = f"{school_abbr}{logo_ext}"
        school_logo.save(
            os.path.join(
                current_app.config["UPLOAD_FOLDER"], "SchoolLogo", logofilename
            )
        )

        # Convert To SVG
        # svg = img2svg(os.path.join(
        # 	current_app.config['UPLOAD_FOLDER'], 'SchoolLogo', logofilename))
        # if(svg['status'] == 200):
        # 	print(svg)

        # os.remove(os.path.join(
        # 	current_app.config['UPLOAD_FOLDER'], 'SchoolLogo', logofilename))

        # Hash Password
        # hashed_password = bcrypt.generate_password_hash(
        # password).decode('utf-8')
        hashed_password = generate_password_hash(password)
        # Add   to Database
        new_school = School(
            admin_username=admin_username,
            schoolname=school_name,
            school_abbr=school_abbr,
            email=email,
            password=hashed_password,
            school_logo=logofilename,
        )
        db.session.add(new_school)
        db.session.commit()

        # Generate Logo Directory
        import os

        path = f"{os.getcwd()}/VoteFlow{url_for('static', filename='DataStore')}"
        os.mkdir(f"{path}/{school_abbr}")

        flash("Successfully Created Account! Please Login to VoteFlow", "success")
        return redirect(url_for("users.school_login"))
    return render_template("register.html", title="Register - VoteFlow", form=form)


@users.route("/<school_abbr>/<poll_name>/login", methods=["GET", "POST"])
def student_login(school_abbr, poll_name):
    return render_template(
        "studentlogin.html", title=f"Login - {poll_name}", school=school_abbr
    )
