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
from EduVoteFlow.auth.utils import abbr_str, get_file_extension
from EduVoteFlow.election.forms import StudentLogin

from EduVoteFlow import db  # , bcrypt
from EduVoteFlow.models import School, Poll, Student, User
from EduVoteFlow.auth.forms import SchoolLogin, SchoolRegister
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import or_

# from .utils import img2svg

# Register this Page as a Blueprint
auth = Blueprint("auth", __name__)


# All Routes
@auth.route("/", methods=["GET", "POST"])
def auth_home():
    if request.method == "POST":
        form = request.form
        poll_id, school_id = int(form["election-id"]), int(form["school-id"])
        if Poll.query.filter_by(id=poll_id, school_id=school_id).first():
            return redirect(
                url_for("auth.student_login", school_id=school_id, poll_id=poll_id)
            )
        flash("School ID or Election ID is Incorrect", "danger")
    return render_template("auth/auth-home.html")


@auth.route("/login", methods=["GET", "POST"])
def school_login():
    form = SchoolLogin()
    if form.validate_on_submit():
        school = School.query.filter_by(
            admin_username=form.admin_username.data.lower()
        ).first()

        if not school:
            flash(
                "School Doesn't Exist,Check Well the Admin User Name or School Abbr",
                "danger",
            )
        elif not check_password_hash(school.password, form.password.data):
            flash(
                f"Password for School is Wrong!!",
                "danger",
            )

        else:
            user = User.query.filter_by(user_type="school", user_id=school.id).first()
            login_user(user, remember=form.remember.data)
            return redirect(url_for("polls.polls_home"))

    return render_template(
        "auth/school-login.html", title="Login - EduVoteFlow", form=form
    )


@auth.route("/register", methods=["GET", "POST"])
def school_register():
    form = SchoolRegister()
    if form.validate_on_submit():
        # Get Form Data
        school_name = request.form["school_name"].title()
        school_abbr = abbr_str(school_name)
        admin_username = request.form["admin_username"].lower()
        password = request.form["password"]
        email = request.form["email"]
        school_logo = request.files["school_logo"]

        # check is if any of school_name,admin_username or email exists
        any_schools = School.query.filter(
            or_(
                School.name == school_name,
                School.admin_username == admin_username,
                School.email == email,
            )
        )
        # if no school having that same info
        if not any_schools.all():
            # Save Logo
            import os.path

            logo_path = url_for("static", filename=f"DataStore/SchoolLogo/default.svg")

            logo_ext = get_file_extension(school_logo.filename)  # Get Extension

            if logo_ext:
                logofilename = f"{school_abbr}{logo_ext}"
                school_logo.save(
                    os.path.join(
                        current_app.config["UPLOAD_FOLDER"], "SchoolLogo", logofilename
                    )
                )
                logo_path = url_for(
                    "static",
                    filename=f"DataStore/SchoolLogo/{logofilename}",
                )

                # os.remove(os.path.join(
                # 	current_app.config['UPLOAD_FOLDER'], 'SchoolLogo', logofilename))

            # Hash Password
            # hashed_password = bcrypt.generate_password_hash(
            # password).decode('utf-8')
            hashed_password = generate_password_hash(password)
            # Add   to Database
            new_school = School(
                admin_username=admin_username,
                name=school_name,
                abbr=school_abbr,
                email=email,
                password=hashed_password,
                logo=logo_path,
            )
            db.session.add(new_school)
            db.session.commit()

            new_user = User(user_type="school", user_id=new_school.id)
            db.session.add(new_user)
            db.session.commit()
            # Generate Logo Directory
            import os

            path = f"{os.getcwd()}/EduVoteFlow{url_for('static', filename='DataStore')}"
            os.mkdir(f"{path}/{school_abbr}{new_school.id}")

            flash(
                "Successfully Created Account! Please Login to EduVoteFlow", "success"
            )
            return redirect(url_for("auth.school_login"))
        else:
            flash(
                "Either 'School Name' , 'Admin Username'  or  'Email'  already taken, Use other unique Info",
                "danger",
            )
    return render_template(
        "auth/school-register.html", title="Register - EduVoteFlow", form=form
    )


@auth.route("/<school_id>/<poll_id>/studentlogin", methods=["GET", "POST"])
def student_login(school_id, poll_id):
    school = School.query.filter_by(id=school_id).first()
    poll = Poll.query.filter_by(id=poll_id).first()
    form = StudentLogin()
    if form.validate_on_submit():
        username = request.form["username"]
        password = request.form["password"].upper()
        student = Student.query.filter_by(
            school_id=school.id,
            poll_id=poll.id,
            username=username,
            password=password,
        ).first()
        print(username, password, student)
        if not student:
            flash(
                "Either the Username or the Password is Incorrect. Please check Credentials. Do not ignore the Case",
                "danger",
            )
            return redirect(
                url_for("auth.student_login", school_id=school.id, poll_id=poll_id)
            )

        if student.voted:
            flash("A Single User cannot Vote more than Once!", "danger")
            return redirect(
                url_for(
                    "auth.student_login",
                    school_id=school.id,
                    poll_id=poll_id,
                )
            )

        user = User.query.filter_by(user_type="student", user_id=student.id).first()
        login_user(user, remember=True)
        return redirect(
            url_for(
                "election.voting_page",
                school_id=school.id,
                poll_id=poll_id,
                s_id=student.id,
            )
        )
    return render_template(
        "auth/student-login.html",
        title="Election",
        school=school,
        poll=poll,
        form=form,
        poll_name=poll.name,
    )


@auth.route("/logout")
@login_required
def user_logout():
    user = current_user
    if isinstance(user, Student):
        user.voted = True
        poll = Poll.query.get(user.poll_id)
        poll.total_voted += 1
        db.session.commit()
        logout_user()
        return render_template("election/congrats.html", title="EduVoteFlow")
    logout_user()
    return redirect(url_for("auth.school_login"))
