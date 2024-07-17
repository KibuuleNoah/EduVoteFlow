# imports
from flask import (
    abort,
    render_template,
    request,
    Blueprint,
    flash,
    redirect,
    url_for,
    jsonify,
    current_app,
    send_from_directory,
)
from flask_wtf.csrf import os
from VoteFlow.models import (
    School,
    Poll,
    Student,
    FlaggedStudent,
    Candidate,
    CandidateResult,
    User,
)
from flask_login import login_required, current_user as current_school
from VoteFlow import db
from VoteFlow.polls.forms import (
    CreatePollForm,
    AddStudentsForm,
    AddCandidatesForm,
    AddStudentForm,
    AddCandidateForm,
    EditFlaggedUsernameForm,
)
import io
from .utils import (
    created_student_password,
    created_student_username,
    extract_excel_data,
    flag_duplicate_usernames,
    active_sched_poll_required,
    get_opposed_candidates,
    get_unopposed_candidates,
    get_poll_link,
    save_candidates,
    created_student_user,
)
from werkzeug.utils import secure_filename
from xlwt import Workbook

# Register this Page as a Blueprint
polls = Blueprint("polls", __name__)

# All Routes


@polls.route("/", methods=["GET", "POST"])
@login_required
def home():
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


@polls.route("/createpoll", methods=["GET", "POST"])
@login_required
def create_poll():
    form = CreatePollForm()
    if form.validate_on_submit():
        # Get Data
        poll_name, houses = (
            request.form["name"],
            request.form["houses"],
        )
        posts, year = request.form["posts"], request.form["year"]
        # Process Data
        posts_splitted = [x.rstrip() for x in posts.split(",")]
        houses_splitted = [x.rstrip() for x in houses.split(",")]

        # Add Data to Database
        new_poll = Poll(
            school_id=current_school.id,
            name=poll_name,
            houses=houses_splitted,
            posts=posts_splitted,
            year=year,
            status="Scheduled",
        )
        db.session.add(new_poll)
        db.session.commit()

        # Generate Logo Directory
        import os

        path = f"{os.getcwd()}/VoteFlow{url_for('static', filename='DataStore')}"
        poll = Poll.query.filter_by(name=poll_name, school_id=current_school.id).first()
        os.mkdir(f"{path}/{current_school.abbr}/{poll.id}")

        flash(f"Successfully Created Poll '{poll_name}'", "success")
        return redirect(url_for("polls.home"))
    return render_template(
        "createpoll.html", title="Create Poll", form=form, nocontainer=True
    )


@polls.route("/<poll_id>/", methods=["GET", "POST"])
@login_required
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
@login_required
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
@login_required
@active_sched_poll_required
def add_students(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    form = AddStudentsForm()
    loaded_students = poll.students
    flagged = []
    if form.validate_on_submit():
        studentMetadata = []
        studentDataFile = request.files["students"]
        studentsBytes = io.BytesIO(studentDataFile.read())
        students = extract_excel_data(studentsBytes)

        # Add to Database
        created_students = []
        for student in students:
            new_student = Student(
                school_id=school.id,
                poll_id=poll.id,
                full_name=student["student_name"].strip(),
                grade=student["grade"],
                section=student["section"],
                roll_no=student["roll_no"],
                gender=student["gender"],
                house=student["house"],
                voted=False,
                username=created_student_username(
                    student["student_name"],
                    student["grade"],
                    student["section"],
                ),
                password=created_student_password(
                    student["grade"],
                    student["section"],
                    student["roll_no"],
                ),
            )
            created_students.append(new_student)
        # Adds everything to the session
        db.session.bulk_save_objects(created_students)
        db.session.commit()  # Commits to database

        for student in poll.students:
            created_student_user(student, db)

        # Check For Duplicates

        # Generate Metadata for Every Student
        for student in set(poll.students):
            studentMetadata.append(
                {
                    "id": student.id,
                    "full_name": student.full_name,
                    "username": student.username,
                    "roll_no": student.roll_no,
                }
            )

        # Initiate Flagging Procedure {DuplicateUsernames are not allowed and will be flagged}
        flagged = flag_duplicate_usernames(studentMetadata)

        # Add it to the Flagged DB
        flagged_students = []
        for student in flagged:
            flagged_student = FlaggedStudent(
                student_id=student.id, poll_id=poll.id, school_id=school.id
            )
            flagged_students.append(flagged_student)
        db.session.bulk_save_objects(flagged_students)
        db.session.commit()

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
@login_required
@active_sched_poll_required
def edit_flagged_students(poll_id):
    school = current_school
    poll = Poll.query.filter_by(id=poll_id).first()
    flagged = FlaggedStudent.query.filter_by(school_id=school.id, poll_id=poll_id).all()
    form = EditFlaggedUsernameForm()
    if request.method == "GET":
        flagged_students = []
        for f in flagged:
            student = Student.query.filter_by(id=f.student_id).first()
            flagged_students.append(student)
        return render_template(
            "polldashboard/editflaggedstudents.html",
            title="Edit Flagged Students",
            flagged=flagged_students,
            school=school,
            dash_location="Resolve-Conflicts",
            poll=poll,
            form=form,
        )
    elif request.method == "POST":
        n = len(flagged)
        usernames = [request.form[f"d{i}"] for i in range(n)]
        students = [Student.query.filter_by(id=f.student_id).first() for f in flagged]
        print(usernames)
        for record, username in zip(students, usernames):
            print(f"RECORD {record.username} -> {username}")
            record.username = username
            db.session.add(record)
            # Remove the Flagged Student
            db.session.delete(
                FlaggedStudent.query.filter_by(
                    school_id=school.id, poll_id=poll.id, student_id=record.id
                ).first()
            )
        db.session.commit()
        flash("Successfully Edited All Usernames!", "success")
        return redirect(
            url_for(
                "polls.edit_flagged_students",
                poll_id=poll_id,
            )
        )


@polls.route("/<poll_id>/addcandidates", methods=["GET", "POST"])
@login_required
@active_sched_poll_required
def add_candidates(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    form = AddCandidatesForm()
    loaded_candidates = (
        poll.candidates
    )  # Candidate.query.filter_by(school=school.abbr, poll=poll.id).all()
    if form.validate_on_submit():
        candidatesDataFile = request.files["candidates"]
        logoBundle = request.files["candidates_logo"]
        candidatesBytes = io.BytesIO(candidatesDataFile.read())
        candidates = extract_excel_data(candidatesBytes)

        # Save the Logo Bundle
        import os

        filename = (
            f"{school.abbr}-{poll.id}-candidates.{(logoBundle.filename).split('.')[1]}"
        )
        logoBundle.save(
            os.path.join(current_app.config["UPLOAD_FOLDER"], secure_filename(filename))
        )

        # Get the Election Type
        posts = poll.posts

        save_candidates(school, poll, posts, candidates, db)

        # Extract the Zip File
        import zipfile
        import os

        path = f"{os.getcwd()}/VoteFlow{url_for('static', filename='DataStore')}"

        with zipfile.ZipFile(f"{path}/{filename}", "r") as zip_ref:
            zip_ref.extractall(f"{path}/{school.id}/{poll_id}/")

        # Add Files to Name
        import glob

        for filepath in glob.iglob(f"{path}/{school.id}/{poll_id}/*.jpg"):
            img_name = os.path.basename(filepath).replace("_", " ")
            print(img_name)
            candidate = Candidate.query.filter_by(
                full_name=img_name.split(".")[0].replace("_", " "),
                poll_id=poll_id,
                school_id=school.id,
            ).first()
            if candidate:
                candidate.logo = os.path.basename(filepath)

            # else:
            #     candidate.logo = os.path.basename(filepath)
            db.session.commit()

        # Remove the Zip File
        os.remove(f"{path}/{filename}")
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
@login_required
def add_student(poll_id):
    school = current_school
    student = request.form
    print(student)
    new_student = Student(
        school_id=school.id,
        poll_id=poll_id,
        full_name=student["student_name"].strip(),
        grade=student["grade"],
        section=student["section"],
        roll_no=student["roll_no"],
        gender=student["gender"],
        house=student["house"],
        voted=False,
        username=created_student_username(
            student["student_name"],
            student["grade"],
            student["section"],
        ),
        password=created_student_password(
            student["grade"],
            student["section"],
            student["roll_no"],
        ),
    )
    db.session.add(new_student)
    db.session.commit()

    created_student_user(new_student, db)
    # Generate Metadata for Every Student
    studentMetadata = {
        "id": new_student.id,
        "full_name": new_student.full_name,
        "username": new_student.username,
        "roll_no": new_student.roll_no,
    }

    # Initiate Flagging Procedure {DuplicateUsernames are not allowed and will be flagged}
    flagged = flag_duplicate_usernames([studentMetadata])
    if flagged:
        # Add it to the Flagged DB
        flagged_student = FlaggedStudent(
            student_id=new_student.id, poll_id=poll.id, school_id=school.id
        )
        db.session.add(flagged_student)
        db.session.commit()
        flash("The Student Your added is flagged first resolve the issue", "danger")
    else:
        flash(f"Added Student {new_student.full_name} successfully")

    return redirect(url_for("polls.manage_students", poll_id=poll_id))


@polls.route("/<poll_id>/delete-student/<s_id>/")
@login_required
def delete_student(poll_id, s_id):
    school = current_school
    student = Student.query.filter_by(
        school_id=school.id, poll_id=poll_id, id=s_id
    ).first()
    if student:
        db.session.delete(student)
        db.session.commit()
        flash(f"student {student.full_name} successfully removed", "success")
    else:
        flash(f"failed to remove student", "danger")
    return redirect(url_for("polls.manage_students", poll_id=poll_id))


@polls.route("/<poll_id>/delete-all-students/")
@login_required
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
@login_required
def delete_all_candidates(poll_id):
    school = current_school
    poll = Poll.query.filter_by(id=poll_id, school_id=school.id).first()
    if poll:
        for candidate in poll.candidates:
            db.session.delete(candidate)
        db.session.commit()
        flash(f"All candidates successfully cleared", "success")
    else:
        flash(f"failed to remove candidates", "danger")
    return redirect(url_for("polls.manage_candidates", poll_id=poll_id))


@polls.route("/<poll_id>/addcandidate", methods=["POST"])
@login_required
def add_candidate(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    form = request.form
    candidate_logo = request.files["logo"]

    new_candidate = Candidate(
        full_name=form["candidate_name"],
        post=form["post"],
        house=form["house"],
        gender=form["gender"],
        logo="",
        slogan=form["slogan"],
        school_id=school.id,
        poll_id=poll.id,
    )
    db.session.add(new_candidate)
    # db.session.commit()

    img_name = f"{new_candidate.full_name}-{new_candidate.id}".replace(" ", "_").lower()
    static_path = url_for(
        "static", filename=f"DataStore/{school.id}/{poll_id}/{img_name}.jpg"
    )
    path = f"{os.getcwd()}/VoteFlow{static_path}"

    candidate_logo.save(path + img_name)
    new_candidate.logo = static_path
    db.session.commit()

    return redirect(url_for("polls.manage_candidates", poll_id=poll_id))


@polls.route("/<poll_id>/delete-candidate/<c_id>/")
@login_required
def delete_candidate(poll_id, c_id):
    school = current_school
    candidate = Candidate.query.filter_by(
        school_id=school.id, poll_id=poll_id, id=c_id
    ).first()
    if candidate:
        db.session.delete(candidate)
        db.session.commit()
        flash(f"Candidate {candidate.full_name} successfully removed", "success")
    else:
        flash(f"failed to remove Candidate", "danger")
    return redirect(url_for("polls.manage_candidates", poll_id=poll_id))


@polls.route("/<poll_id>/startelection", methods=["GET"])
@login_required
@active_sched_poll_required
def start_election(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()

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
    else:
        poll.status = "Active"
        db.session.commit()
        flash(
            f"Poll ({poll.name}) has been officially started and is currently active!",
            "success",
        )
    return redirect(url_for("polls.dashboard_home", poll_id=poll.id))


@polls.route("/<poll_id>/deletepoll", methods=["GET", "POST"])
@login_required
@active_sched_poll_required
def delete_poll(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    if request.method == "POST":
        # Delete Students
        [db.session.delete(s) for s in poll.students]
        # Delete Candidates
        [db.session.delete(n) for n in poll.candidates]
        # Delete Poll
        db.session.delete(poll)
        db.session.commit()
        flash(f"Successfully Deleted Poll ({poll.name})", "success")
        return redirect(url_for("polls.home"))
    return render_template(
        "polldashboard/deletepoll.html",
        title=poll.name,
        dash_location="Close-Poll",
        school=school,
        poll=poll,
    )


@polls.route("/<poll_id>/results", methods=["GET", "POST"])
@login_required
@active_sched_poll_required
def results(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    if request.method == "POST":
        poll.status = "Archived"
        all_results = []
        for post in poll.posts:
            candidates = poll.candidates
            votes = [x.votes for x in candidates]
            winner = candidates[votes.index(max(votes))]
            all_results.append(
                CandidateResult(
                    school_id=school.id,
                    poll_id=poll_id,
                    candidate_id=winner.id,
                    votes=winner.votes,
                )
            )
        db.session.bulk_save_objects(all_results)
        db.session.commit()
        for winner in CandidateResult.query.filter_by(
            school_id=school.id, poll_id=poll_id
        ):
            print(f"{winner.post} -> {winner.full_name}: {winner.votes}")

        # TODO: DELETE candidateS
        # TODO: DELETE STUDENTS
        return redirect(
            url_for(
                "polls.results_page",
                poll_id=poll_id,
            )
        )

    return render_template(
        "polldashboard/results.html",
        title=poll.name,
        school=school,
        dash_location="Results",
        poll=poll,
    )


@polls.route("/<poll_id>/resultspage", methods=["GET", "POST"])
@login_required
def results_page(poll_id):
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    if poll.status == "Archived":
        results = CandidateResult.query.filter_by(
            school_id=school.id, poll_id=poll_id
        ).all()
        stats = (
            len(
                Student.query.filter_by(
                    voted=True, school_id=school.id, poll_id=poll.id
                ).all()
            ),
            len(poll.students),
        )
        print(results)
        return render_template(
            "polldashboard/resultsdisplay.html",
            title="Results",
            res=results,
            polltype="A2A",
            stats=stats,
            school=school,
            dash_location="Results",
            poll_id=poll_id,
        )
    else:
        flash("Cannot Declare Results for an Active Poll", "danger")
        return redirect(
            url_for(
                "polls.dashboard_home",
                poll_id=poll_id,
            )
        )
    return render_template("polldashboard/resultsdisplay.html", title="Results")


@polls.route("/<poll_id>/manage-students", methods=["GET", "POST"])
@login_required
@active_sched_poll_required
def manage_students(poll_id):
    form = AddStudentForm()
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    students = (
        poll.students
    )  # Student.query.filter_by(school=school_abbr, poll=poll_id).all()
    print(school)
    houses = ["RUBY", "TOPAZ", "EMERALD", "SAPPHIRE"]
    if request.method == "POST":
        gender = request.form["gender"]
        house = None
        # if "A2A" == "GH-I2I":
        #     house = request.form["house"]
        #     if gender.split("-")[0] == house.split("-")[0]:
        #         s_id = gender.split("-")[0]
        #         student = Student.query.filter_by(id=s_id).first()
        #         student.house = house.split("-")[1]
        #         student.gender = gender.split("-")[1]
        #         db.session.commit()
        #         flash(
        #             f"Student ('{student.full_name}') updated successfully", "success"
        #         )
        # else:
        #     if gender.split("-")[0]:
        #         s_id = gender.split("-")[0]
        #         student = Student.query.filter_by(id=s_id).first()
        #         # student.house = house.split('-')[1]
        #         student.gender = gender.split("-")[1]
        #         db.session.commit()
        #         flash(
        #             f"Student ('{student.full_name}') updated successfully", "success"
        #         )
    print(students)
    return render_template(
        "polldashboard/manage-students.html",
        title="manage-students",
        students=students,
        poll=poll,
        school=school,
        form=form,
        dash_location="Manage Students",
        houses=houses,
        p_type="A2A",
        p_name=poll.name,
    )


@polls.route("/<poll_id>/manage-candidates", methods=["GET", "POST"])
@login_required
@active_sched_poll_required
def manage_candidates(poll_id):
    form = AddCandidateForm()
    school = current_school
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    candidates = poll.candidates

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
@login_required
def downloadelectionsummary(poll_id):
    import os

    poll = Poll.query.filter_by(school_id=current_school.id, id=poll_id).first()
    candidates = poll.candidates
    # Candidate.query.filter_by(school.id=school_abbr, poll=poll_id).all()
    wb = Workbook()
    s = wb.add_sheet("Sheet 1")

    s.write(0, 0, "candidate_name")
    s.write(0, 1, "post")
    s.write(0, 2, "house")
    s.write(0, 3, "gender")
    s.write(0, 4, "votes")

    for i, candidate in enumerate(candidates):
        full_name = candidate.full_name
        post = None
        if "A2A" == "GH-I2I":
            post = candidate.post.split("-")[2][1:-1]
        elif "A2A" == "G-I2I":
            post = candidate.post.split("-")[1][1:-1]
        house = candidate.house
        gender = candidate.gender
        votes = candidate.votes

        s.write(i + 1, 0, str(full_name))
        s.write(i + 1, 1, str(post))
        if house == "ANY":
            s.write(i + 1, 2, "")
        else:
            s.write(i + 1, 2, str(house))
        s.write(i + 1, 3, str(gender))
        s.write(i + 1, 4, int(votes))

    wb.save(
        os.path.join(current_app.config["UPLOAD_FOLDER"], f"Poll-{poll_id}-Summary.xls")
    )
    return send_from_directory(
        os.path.join(current_app.config["UPLOAD_FOLDER"]),
        filename=f"Poll-{poll_id}-Summary.xls",
    )


@polls.route("/<poll_id>/downloadabsenteevoterslist", methods=["GET", "POST"])
@login_required
def download_absentee_voters_list(school_abbr, poll_id):
    import os

    voters = Student.query.filter_by(
        school=school_abbr, poll=poll_id, voted=False
    ).all()
    poll = Poll.query.filter_by(id=poll_id).first()
    wb = Workbook()
    s = wb.add_sheet("Sheet 1")

    s.write(0, 0, "student_name")
    s.write(0, 1, "grade")
    s.write(0, 2, "section")

    for i, voter in enumerate(voters):
        full_name = voter.full_name
        grade = voter.grade
        section = voter.section

        s.write(i + 1, 0, str(full_name))
        s.write(i + 1, 1, str(grade))
        s.write(i + 1, 2, str(section))

    wb.save(
        os.path.join(
            current_app.config["UPLOAD_FOLDER"], f"Poll-{poll_id}-AbsenteeList.xls"
        )
    )
    return send_from_directory(
        os.path.join(current_app.config["UPLOAD_FOLDER"]),
        filename=f"Poll-{poll_id}-AbsenteeList.xls",
    )
