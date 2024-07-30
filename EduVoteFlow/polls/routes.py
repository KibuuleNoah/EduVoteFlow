# imports
import zipfile
from flask import (
    abort,
    render_template,
    request,
    Blueprint,
    flash,
    redirect,
    url_for,
    jsonify,
    send_from_directory,
)
from flask import current_app as cur_app
from flask_wtf.csrf import os
import openpyxl
from EduVoteFlow.auth.utils import get_file_extension, schoolloginrequired
from EduVoteFlow.election.routes import activepollrequired
from EduVoteFlow.election.utils import prepare_candidates
from EduVoteFlow.models import (
    School,
    Poll,
    Student,
    FlaggedStudent,
    Candidate,
    User,
)
from flask_login import login_required, current_user as current_school
from EduVoteFlow import db
from EduVoteFlow.polls.forms import (
    CreatePollForm,
    AddStudentsForm,
    AddCandidatesForm,
    AddStudentForm,
    AddCandidateForm,
    EditFlaggedUsernameForm,
)
import io

from .utils import (
    create_student_password,
    create_student_username,
    extract_excel_data,
    flag_duplicate_usernames,
    active_sched_poll_required,
    get_gender,
    get_opposed_candidates,
    get_schpolldir_path,
    get_unopposed_candidates,
    get_poll_link,
    save_candidates,
    created_student_user,
    scheduledpollrequired,
    rank_candidates_by_post,
    validate_student_cols,
)
from werkzeug.utils import secure_filename
from openpyxl import Workbook
import shutil

# Register this Page as a Blueprint
polls = Blueprint("polls", __name__)

# All Routes


@polls.route("/", methods=["GET", "POST"])
@schoolloginrequired
def polls_home():
    form = CreatePollForm()
    if form.is_submitted():
        return redirect(url_for("polls.create_poll"))

    school = current_school
    # Getting Polls From Database
    activepolls = Poll.query.filter_by(school_id=school.id, status="Active").all()
    scheduledpolls = Poll.query.filter_by(school_id=school.id, status="Scheduled").all()
    archivedpolls = Poll.query.filter_by(school_id=school.id, status="Archived").all()

    return render_template(
        "polls-home.html",
        title="Dashboard-Polls",
        dash_location="polls",
        school=school,
        activepolls=activepolls,
        scheduledpolls=scheduledpolls,
        archivedpolls=archivedpolls,
        form=form,
        linker=get_poll_link,  # (school.id,poll.id),
    )
    # flash("You cannot access another user's dashboard!", "danger")
    # return redirect(url_for("polls.polls-home", school_abbr=current_user.abbr))


@polls.route("/createpoll", methods=["POST"])
@schoolloginrequired
def create_poll():
    school = current_school
    # Get Data
    poll_name, houses = (
        request.form["name"].title(),
        request.form["houses"].title(),
    )
    posts, year = request.form["posts"].title(), request.form["year"]
    # Process Data
    posts_splitted = [x.rstrip() for x in posts.split(",")]
    houses_splitted = [x.rstrip() for x in houses.split(",")]

    # check if the same school already
    # has a poll with the same name
    poll_name_exists = Poll.query.filter_by(name=poll_name, school_id=school.id).all()

    # if that poll doesn't exists
    if not poll_name_exists:
        # Add New Poll to Database
        new_poll = Poll(
            school_id=school.id,
            name=poll_name,
            houses=houses_splitted,
            posts=posts_splitted,
            year=year,
            status="Scheduled",
        )
        db.session.add(new_poll)
        db.session.commit()

        # Generate Poll Logo Directory
        import os

        path = f"{cur_app.config['APP_PATH']}/{cur_app.config['APP_NAME']}{url_for('static', filename='media')}"
        os.mkdir(f"{path}/{school.abbr}{school.id}/{new_poll.id}")

        flash(f"Successfully Created Poll '{poll_name}'", "success")
    else:
        flash(f"Poll With Name '{poll_name}' Already Exists", "warning")
    return redirect(url_for("polls.polls_home"))


@polls.route("/<poll_id>/", methods=["GET", "POST"])
@schoolloginrequired
@active_sched_poll_required
def dashboard_home(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    if not poll:
        abort(404)
    link = get_poll_link(school.id, poll.id) if poll.status == "Active" else ""

    len_candidates = len(poll.candidates)
    len_students = len(poll.students)

    # All unopposed candidates from the current poll
    unopposed = get_unopposed_candidates(poll.id, school.id).all()
    # Top candidates with many votes
    top_candidates = (
        get_opposed_candidates(poll.id, school.id)
        .order_by(Candidate.votes.desc())
        .limit(5)
        .all()
    )
    print("POSTS", poll.posts)
    return render_template(
        "polldashboard/home.html",
        title=poll.name,
        school=school,
        dash_location="Home",
        poll=poll,
        top_candidates=top_candidates,
        unopposed=unopposed,
        status=poll.status,
        link=link,
        len_cand=len_candidates,
        len_stud=len_students,
    )


@polls.route("/<poll_id>/settings", methods=["GET", "POST"])
@schoolloginrequired
@active_sched_poll_required
def general_settings(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    if not poll:
        abort(404)
    return render_template(
        "polldashboard/settings.html",
        title=poll.name,
        dash_location="Settings",
        school=school,
        poll=poll,
    )


@polls.route("/<poll_id>/addstudents", methods=["GET", "POST"])
@schoolloginrequired
@scheduledpollrequired
def add_students(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    form = AddStudentsForm()
    loaded_students = poll.students
    flagged = []
    if form.validate_on_submit():
        students_metadata = []
        student_data_file = request.files["students"]
        students_bytes = io.BytesIO(student_data_file.read())
        # check if the submitted file is a valid excel
        try:
            students = extract_excel_data(students_bytes)
        except:
            flash("The Students Excel File In Invaild", "danger")
            return redirect(url_for("polls.add_students", poll_id=poll_id))

        if not validate_student_cols(students):
            flash("The excel tabel your provided is missing some columns", "danger")
            return redirect(url_for("polls.add_students", poll_id=poll.id))

        created_students = []
        for student in students:
            password = create_student_password(
                student.get("grade", ""),
                student.get("section", ""),
                student.get("roll_no", ""),
            )
            username = create_student_username(
                student.get("name", ""),
                student.get("grade", ""),
                student.get("section", ""),
            )

            new_student = Student(
                school_id=school.id,
                poll_id=poll.id,
                name=student.get("name", "").strip().title(),
                grade=student.get("grade", ""),
                section=student.get("section", ""),
                roll_no=student.get("roll_no", 0),
                gender=get_gender(student.get("gender", "")),
                house=student.get("house", ""),
                username=username,
                password=password,
            )
            created_students.append(new_student)

        # Adds everything to the session
        db.session.bulk_save_objects(created_students)
        db.session.commit()  # Commits to database

        # Check For Duplicates
        # Generate Metadata for Every Student
        for student in set(poll.students):
            students_metadata.append(
                {
                    "id": student.id,
                    "name": student.name,
                    "username": student.username,
                    "roll_no": student.roll_no,
                }
            )

        # Initiate Flagging Procedure {DuplicateUsernames are not allowed and will be flagged}
        flagged = flag_duplicate_usernames(students_metadata)

        # Add it to the Flagged DB
        flagged_students = []
        for student in flagged:
            flagged_student = FlaggedStudent(
                student_id=student.id, poll_id=poll.id, school_id=school.id
            )
            flagged_students.append(flagged_student)
        db.session.bulk_save_objects(flagged_students)
        db.session.commit()

        # create student user for none flaged students
        for student in poll.students:
            if student not in flagged_students:
                created_student_user(student, db)

        flash("Successfully Added Students!", "success")
        return render_template(
            "polldashboard/addstudents.html",
            title=poll.name,
            school=school,
            dash_location="Add-Students",
            poll=poll,
            form=form,
            flagged=flagged,
            host=request.host_url[:-1],
        )

    flagged = FlaggedStudent.query.filter_by(poll_id=poll.id, school_id=school.id).all()
    if loaded_students:
        return render_template(
            "polldashboard/addstudents.html",
            title=poll.name,
            school=school,
            dash_location="Add-Students",
            poll=poll,
            form=form,
            flagged=flagged,
        )
    return render_template(
        "polldashboard/addstudents.html",
        title=poll.name,
        school=school,
        dash_location="Add-Students",
        poll=poll,
        form=form,
        loaded=True,
    )


@polls.route("/<poll_id>/editflaggedstudents", methods=["GET", "POST"])
@schoolloginrequired
@active_sched_poll_required
def edit_flagged_students(poll_id):
    school = current_school
    poll = Poll.query.filter_by(id=poll_id, school_id=school.id).first()
    flagged = FlaggedStudent.query.filter_by(school_id=school.id, poll_id=poll_id).all()
    form = EditFlaggedUsernameForm()

    if request.method == "POST":
        len_flagged = len(flagged)
        len_edited = 0
        usernames = [request.form[f"d{i}"] for i in range(len_flagged)]
        students = [Student.query.get(fd.student_id) for fd in flagged]
        print(usernames)
        for student, username in zip(students, usernames):
            if len(username) > 5 and student.username != username:
                student.username = username
                # db.session.add(record)
                # Remove the Flagged Student
                db.session.delete(
                    FlaggedStudent.query.filter_by(
                        school_id=school.id, poll_id=poll.id, student_id=student.id
                    ).first()
                )
                len_edited += 1
        db.session.commit()
        if len_flagged == len_edited:
            flash("Successfully Edited All Usernames!", "success")
            return redirect(
                url_for(
                    "polls.dashboard_home",
                    poll_id=poll_id,
                )
            )

        else:
            flash(
                f"Successfully Edited {len_edited}/{len_flagged} Usernames!", "success"
            )
            return redirect(
                url_for(
                    "polls.edit_flagged_students",
                    poll_id=poll_id,
                )
            )

    flagged_students = []
    for f in flagged:
        student = Student.query.filter_by(id=f.student_id).first()
        flagged_students.append(student)

    return render_template(
        "polldashboard/editflaggedstudents.html",
        title="Edit Flagged Students",
        dash_location="Edit Flagged Students",
        flagged=flagged_students,
        school=school,
        poll=poll,
        form=form,
    )


@polls.route("/<poll_id>/addcandidates", methods=["GET", "POST"])
@schoolloginrequired
@scheduledpollrequired
def add_candidates(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    form = AddCandidatesForm()
    loaded_candidates = poll.candidates

    if form.validate_on_submit():
        candidates_file = request.files["candidates"]
        logo_bundle = request.files["candidates_logo"]
        candidates_bytes = io.BytesIO(candidates_file.read())

        try:
            candidates = extract_excel_data(candidates_bytes)
        except:
            flash("Candidates Excel file is not a Valid", "danger")
            return redirect(url_for("polls.add_candidates", poll_id=poll_id))

        # Save the Logo Bundle
        filename = (
            f"{school.abbr}-{poll.id}-candidates.{(logo_bundle.filename).split('.')[1]}"
        )
        logoszip_path = os.path.join(
            cur_app.config["UPLOAD_FOLDER"], secure_filename(filename)
        )
        logo_bundle.save(logoszip_path)

        # Get the Election Type
        posts = poll.posts

        if not save_candidates(school, poll, posts, candidates, db):
            flash(
                "File is missing some columns, check well before re-uploading", "danger"
            )
            return redirect(url_for("polls.add_candidates", poll_id=poll_id))

        # Extract the Zip File
        poll_dir = get_schpolldir_path(
            school, poll
        )  # f"{os.getcwd()}/EduVoteFlow{url_for('static', filename='media')}"

        with zipfile.ZipFile(logoszip_path, "r") as zip_ref:
            zip_ref.extractall(poll_dir)

        # Add Files to Name
        import glob

        for filepath in glob.iglob(f"{poll_dir}/*.jpg"):
            img_name = os.path.basename(filepath).replace("_", " ")
            candidate = Candidate.query.filter_by(
                name=img_name.split(".")[0].replace("_", " "),
                poll_id=poll_id,
                school_id=school.id,
            ).first()
            if candidate:
                static_path = "/static" + filepath.split("static")[-1]
                candidate.logo = static_path

        db.session.commit()

        # Remove the Zip File
        os.remove(logoszip_path)
        flash("Successfully Uploaded all candidates!", "success")
        return render_template(
            "polldashboard/addcandidates.html",
            title=poll.name,
            school=school,
            dash_location="Add-Candidates",
            poll=poll,
            form=form,
            loaded=True,
        )

    if loaded_candidates:
        return render_template(
            "polldashboard/addcandidates.html",
            title=poll.name,
            school=school,
            dash_location="Add-Candidates",
            poll=poll,
            form=form,
            loaded=True,
        )
    return render_template(
        "polldashboard/addcandidates.html",
        title=poll.name,
        dash_location="Add-Candidates",
        school=school,
        poll=poll,
        form=form,
    )


@polls.route("/<poll_id>/addstudent", methods=["GET", "POST"])
@schoolloginrequired
@scheduledpollrequired
def add_student(poll_id):
    school = current_school
    student = request.form
    poll = Poll.query.get(poll_id)

    username = create_student_username(
        student.get("name", ""),
        student.get("grade", ""),
        student.get("section", ""),
    )
    password = create_student_password(
        student.get("grade", ""),
        student.get("section", ""),
        student.get("roll_no", ""),
    )
    new_student = Student(
        school_id=school.id,
        poll_id=poll_id,
        name=student.get("name", "").strip().title(),
        grade=student.get("grade", "").title(),
        section=student.get("section", "").upper(),
        roll_no=student.get("roll_no", ""),
        gender=get_gender(student.get("gender", "")),
        house=student.get("house", ""),
        username=username,
        password=password,
    )

    student_usernames = [s.username for s in poll.students]
    db.session.add(new_student)
    db.session.commit()
    if new_student.username in student_usernames:
        # Add it to the Flagged DB
        flagged_student = FlaggedStudent(
            student_id=new_student.id, poll_id=poll.id, school_id=school.id
        )
        db.session.add(flagged_student)
        db.session.commit()
        flash("The Student Your added is flagged first resolve the issue", "danger")
    else:
        created_student_user(new_student, db)
        flash(f"Added Student {new_student.name} successfully", "success")

    return redirect(url_for("polls.manage_students", poll_id=poll_id))


@polls.route("/<poll_id>/delete-student/<s_id>/")
@schoolloginrequired
def delete_student(poll_id, s_id):
    school = current_school
    student = Student.query.filter_by(
        school_id=school.id, poll_id=poll_id, id=s_id
    ).first()
    if student:
        db.session.delete(student)
        db.session.commit()
        flash(f"student {student.name} successfully removed", "success")
    else:
        flash(f"failed to remove student", "danger")
    return redirect(url_for("polls.manage_students", poll_id=poll_id))


@polls.route("/<poll_id>/delete-all-students/")
@schoolloginrequired
def delete_all_students(poll_id):
    school = current_school
    poll = Poll.query.filter_by(id=poll_id, school_id=school.id).first()
    if poll:
        for student in poll.students:
            db.session.delete(student)
        db.session.commit()
        flash(f"All students successfully cleared", "success")
    else:
        flash(f"failed to remove students", "danger")
    return redirect(url_for("polls.manage_students", poll_id=poll_id))


@polls.route("/<poll_id>/delete-all-candidates/")
@schoolloginrequired
def delete_all_candidates(poll_id):
    school = current_school
    poll = Poll.query.filter_by(id=poll_id, school_id=school.id).first()
    if poll:
        for candidate in poll.candidates:
            db.session.delete(candidate)
        db.session.commit()
        path = get_schpolldir_path(school, poll)
        shutil.rmtree(path)
        os.mkdir(path)
        flash(f"All candidates successfully cleared", "success")
    else:
        flash(f"failed to remove candidates", "danger")
    return redirect(url_for("polls.manage_candidates", poll_id=poll_id))


@polls.route("/<poll_id>/addcandidate", methods=["POST"])
@schoolloginrequired
@scheduledpollrequired
def add_candidate(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    form = request.form
    candidate_logo = request.files["logo"]

    new_candidate = Candidate(
        name=form["name"].title(),
        post=form["post"],
        house=form["house"],
        grade=form["grade"].title(),
        gender=get_gender(form.get("gender", "")),
        slogan=form["slogan"].title(),
        school_id=school.id,
        poll_id=poll.id,
    )
    db.session.add(new_candidate)
    db.session.commit()

    if ext := get_file_extension(candidate_logo.filename):
        img_name = f"{new_candidate.names}-{new_candidate.id}{ext}".replace(
            " ", "_"
        ).lower()
        print("****", img_name, ext)
        static_path = url_for(
            "static",
            filename=f"media/{school.abbr}{school.id}/{poll_id}/{img_name}",
        )
        print("****", static_path)
        path = f"{os.getcwd()}/EduVoteFlow{static_path}"
        print("****", path)

        candidate_logo.save(path)
        new_candidate.logo = static_path
        db.session.commit()

    return redirect(url_for("polls.manage_candidates", poll_id=poll_id))


@polls.route("/<poll_id>/delete-candidate/<c_id>/")
@schoolloginrequired
def delete_candidate(poll_id, c_id):
    school = current_school
    candidate = Candidate.query.filter_by(
        school_id=school.id, poll_id=poll_id, id=c_id
    ).first()
    if candidate:
        logo_path = candidate.logo
        # Check is candidate doesn't have a default logo
        if logo_path.split("/")[-1] != "default.jpg":
            # get full path to candidate's logo
            full_path = (
                cur_app.config["APP_PATH"]
                + f"/{cur_app.config['APP_NAME']}"
                + logo_path
            )
            os.remove(full_path)
        db.session.delete(candidate)
        db.session.commit()
        flash(f"Candidate {candidate.names} successfully removed", "success")
    else:
        flash(f"failed to remove Candidate", "danger")
    return redirect(url_for("polls.manage_candidates", poll_id=poll_id))


@polls.route("/<poll_id>/startelection", methods=["GET"])
@schoolloginrequired
@active_sched_poll_required
def start_election(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    flagged_students = FlaggedStudent.query.filter_by(
        poll_id=poll.id, school_id=school.id
    ).all()

    if poll.status == "Active":
        flash(
            f"Poll ({poll.name}) Already officially started",
            "success",
        )
        return redirect(url_for("polls.dashboard_home", poll_id=poll.id))

    if len(poll.students) == 0:
        flash("Please You Must Add Students to vote", "danger")
    elif len(poll.candidates) == 0:
        flash("Please You Must Add Candidates to be voted", "danger")
    elif flagged_students:
        flash("Please You Must First Resolve Flagged Students", "danger")
    else:
        poll.status = "Active"
        db.session.commit()
        flash(
            f"Poll ({poll.name}) has been officially started and is currently active!",
            "success",
        )
    return redirect(url_for("polls.dashboard_home", poll_id=poll.id))


@polls.route("/<poll_id>/deletepoll")
@schoolloginrequired
@active_sched_poll_required
def delete_poll(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    # Delete Students
    [db.session.delete(s) for s in poll.students]
    # Delete Candidates
    [db.session.delete(n) for n in poll.candidates]
    # Delete Poll Dir in static
    path = get_schpolldir_path(school, poll)
    shutil.rmtree(path)
    # Delete Poll
    db.session.delete(poll)
    db.session.commit()
    flash(f"Successfully Deleted Poll ({poll.name})", "success")
    return redirect(url_for("polls.polls_home"))


@polls.route("/<poll_id>/results", methods=["GET", "POST"])
@schoolloginrequired
def results(poll_id):

    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    if poll.status != "Archived":
        poll.status = "Archived"
        db.session.commit()
    opposed = get_opposed_candidates(poll.id, school.id)
    unopposed = get_unopposed_candidates(poll.id, school.id)
    candidates = prepare_candidates(opposed.all())
    cand_rank = rank_candidates_by_post(candidates)
    len_candidates = len(poll.candidates)
    len_students = len(poll.students)

    return render_template(
        "polldashboard/results.html",
        title="Results",
        school=school,
        poll=poll,
        dash_location="Results",
        unopposed_cands=unopposed,
        winners=cand_rank["winners"],
        losers=cand_rank["losers"],
        results=cand_rank["res_obj"],
        len_cand=len_candidates,
        len_stud=len_students,
    )


@polls.route("/<poll_id>/manage-students")
@schoolloginrequired
@active_sched_poll_required
def manage_students(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    form = AddStudentForm(house_choices=poll.houses)
    students = poll.students

    return render_template(
        "polldashboard/manage-students.html",
        title="manage-students",
        students=students,
        poll=poll,
        school=school,
        form=form,
        dash_location="Manage Students",
        p_name=poll.name,
    )


@polls.route("/<poll_id>/manage-candidates", methods=["GET", "POST"])
@schoolloginrequired
@active_sched_poll_required
def manage_candidates(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    candidates = poll.candidates

    post_choices = [(p, p) for p in poll.posts]
    house_choices = [(h, h) for h in poll.houses]

    form = AddCandidateForm(post_choices=post_choices, house_choices=house_choices)

    return render_template(
        "polldashboard/manage-candidates.html",
        title="manage-candidates",
        candidates=candidates,
        poll=poll,
        school=school,
        form=form,
        dash_location="Manage Candidates",
        p_name=poll.name,
    )


@polls.route("/<poll_id>/downloadelectionsummary", methods=["GET", "POST"])
@schoolloginrequired
def downloadelectionsummary(poll_id):
    import os

    poll = Poll.query.filter_by(school_id=current_school.id, id=poll_id).first()
    candidates = poll.candidates
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet 1"

    ws.append(["candidate_name", "post", "house", "gender", "votes"])

    for candidate in candidates:
        candidate_name = candidate.name
        post = candidate.post.split("-")[2][1:-1]
        house = candidate.house
        gender = candidate.gender
        votes = candidate.votes

        ws.append(
            [candidate_name, post, "" if house == "ANY" else house, gender, votes]
        )

    file_path = os.path.join(
        cur_app.config["UPLOAD_FOLDER"], f"Poll-{poll_id}-Summary.xlsx"
    )
    wb.save(file_path)
    return send_from_directory(
        os.path.join(cur_app.config["UPLOAD_FOLDER"]),
        filename=f"Poll-{poll_id}-Summary.xlsx",
    )


@polls.route("/<poll_id>/downloadabsenteevoterslist", methods=["GET", "POST"])
@schoolloginrequired
def download_absentee_voters_list(school_abbr, poll_id):
    import os

    voters = Student.query.filter_by(
        school=school_abbr, poll=poll_id, voted=False
    ).all()
    poll = Poll.query.filter_by(id=poll_id).first()
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet 1"

    ws.append(["student_name", "grade", "section"])

    for voter in voters:
        name = voter.name
        grade = voter.grade
        section = voter.section

        ws.append([name, grade, section])

    file_path = os.path.join(
        cur_app.config["UPLOAD_FOLDER"], f"Poll-{poll_id}-AbsenteeList.xlsx"
    )
    wb.save(file_path)
    return send_from_directory(
        os.path.join(cur_app.config["UPLOAD_FOLDER"]),
        filename=f"Poll-{poll_id}-AbsenteeList.xlsx",
    )
