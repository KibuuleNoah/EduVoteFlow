from flask import abort, flash, url_for, redirect
from functools import wraps
from flask_login import current_user
from flask_wtf.csrf import os
from sqlalchemy import func
from EduVoteFlow.models import Candidate, Poll, School, Student, User, db
from openpyxl import load_workbook


def extract_excel_data(fileobject):
    wb = load_workbook(fileobject, data_only=True)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    data = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        data_object = {
            headers[i]: (row[i] if row[i] is not None else "")
            for i in range(len(headers))
        }
        data.append(data_object)
    print(headers)
    print(data)
    return data


def created_student_username(fullname, grade, section):
    subnames = fullname.strip().split(" ")
    firstname = subnames[0]
    # check for single letter first name
    if len(firstname) > 2:
        return f"{firstname}{grade}{section}"
    return f"{subnames[1]}{grade}{section}"


def created_student_password(grade, section, roll_no):
    return f"{grade}{section}{roll_no}"


# Check For Duplocate usernames and report them.
def flag_duplicate_usernames(data):
    # code to get index of duplicate names
    def list_duplicates_of(seq, item):
        start_at = -1
        locs = []
        while True:
            try:
                loc = seq.index(item, start_at + 1)
            except ValueError:
                break
            else:
                locs.append(loc)
                start_at = loc
        return locs

    # get index of duplicates
    usernames = [data[x]["username"] for x in range(len(data))]
    all_indexes = [list_duplicates_of(usernames, u) for u in usernames]

    # removing duplicate indexes
    duplicateIndexes = []
    for d in all_indexes:
        if len(d) > 1:
            if d not in duplicateIndexes:
                duplicateIndexes.append(d)
    # get duplicate items from indexes
    duplicatedObjects = []
    for e in duplicateIndexes:
        for index in e:
            duplicatedObjects.append(data[index])

    # send back db objects
    student_objects = []
    for i in range(len(duplicatedObjects)):
        student = Student.query.filter_by(
            id=int(duplicatedObjects[i]["id"]), roll_no=duplicatedObjects[i]["roll_no"]
        ).first()
        student_objects.append(student)
    return student_objects


def created_student_user(student: Student, db):
    new_user = User(user_type="student", user_id=student.id)
    db.session.add(new_user)
    db.session.commit()


def active_sched_poll_required(func):
    """
    Active and Scheduled polls required
    """

    @wraps(func)
    def func_wrapper(poll_id):
        poll = Poll.query.filter_by(school_id=current_user.id, id=poll_id).first()
        if not poll:
            abort(404)
        if poll.status != "Archived":
            return func(poll_id)
        else:
            flash(
                f"This Poll has been Archived! The Dashboard cannot be viewed for a Archived Poll",
                "danger",
            )
            return redirect(url_for("polls.home"))

    return func_wrapper


def activepollrequired(func):
    """
    Active polls required
    """

    @wraps(func)
    def func_wrapper(poll_id, *args):
        poll = Poll.query.filter_by(school_id=current_user.id, id=poll_id).first()
        if not poll:
            abort(404)
        if poll.status == "Active":
            return func(poll_id, *args)
        elif poll.status == "Scheduled":
            flash(
                "This Poll hasn't Started, This Action Can't be done on Scheduled Polls",
                "danger",
            )
            return redirect(url_for("polls.dashboard_home", poll_id=poll_id))
        else:
            flash(
                f"This Poll has been {poll.status}! It can't make the task",
                "danger",
            )
            return redirect(url_for("polls.home"))

    return func_wrapper


def scheduledpollrequired(func):
    """
    Scheduled polls required
    """

    @wraps(func)
    def func_wrapper(poll_id, *args):
        poll = Poll.query.filter_by(school_id=current_user.id, id=poll_id).first()
        if not poll:
            abort(404)
        if poll.status == "Scheduled":
            return func(poll_id, *args)
        elif poll.status == "Active":
            flash("This Poll is Already Active,This Action Can't be done", "danger")
            return redirect(url_for("polls.dashboard_home", poll_id=poll_id))
        else:
            flash(
                f"This Poll has been {poll.status}! It can't make the task",
                "danger",
            )
            return redirect(url_for("polls.home"))

    return func_wrapper


def add_record(candidate: dict, school_id: int, poll: Poll):
    candidate_objects = []
    new_candidate = Candidate(
        school_id=school_id,
        poll_id=poll.id,
        full_name=candidate["student_name"],
        house=candidate["house"],
        gender=candidate["gender"],
        post=candidate["post"],
        logo="",
        slogan=candidate["slogan"],
    )
    candidate_objects.append(new_candidate)
    return candidate_objects


def get_poll_link(school_id: int, poll_id: int):
    poll = Poll.query.filter_by(id=poll_id).first()
    return url_for(
        "election.splash_screen", school_id=school_id, poll_id=poll.id, _external=True
    )


def get_unopposed_candidates(poll_id: int, school_id: int):
    unopposed_candidates = (
        Candidate.query.filter_by(poll_id=poll_id, school_id=school_id)
        .group_by(Candidate.post)
        .having(func.count(Candidate.id) == 1)
        # .all()
    )

    return unopposed_candidates

    # def get_unopposed_candidates(db):
    #     unopposed_candidates = (
    #         db.session.query(Candidate)
    #         .group_by(Candidate.post)
    #         .having(func.count(Candidate.id) == 1)
    #         .all()
    #     )

    return unopposed_candidates


def get_opposed_candidates(poll_id, school_id):
    # poll = Poll.query.get(poll_id)
    # print("CANDIDATES", poll.candidates)
    # print()
    # opposed_candidates = (
    #     Candidate.query.filter_by(poll_id=poll_id, school_id=school_id)
    #     .group_by(Candidate.post)
    #     .having(func.count(Candidate.id) > 1)
    #     # .all()
    # )

    # Subquery to find posts with more than one candidate
    subquery = (
        db.session.query(Candidate.post)
        .group_by(Candidate.post)
        .having(func.count(Candidate.id) > 1)
        .subquery()
    )

    # Main query to get all candidates with non-unique posts
    opposed_candidates = Candidate.query.filter(Candidate.post.in_(subquery)).filter_by(
        poll_id=poll_id, school_id=school_id
    )
    return opposed_candidates


def save_candidates(
    school: School, poll: Poll, posts: list[str], candidates: list[dict], db
):
    for post in posts:
        for candidate in candidates:
            if post == candidate["post"]:
                db.session.bulk_save_objects(add_record(candidate, school.id, poll))
                db.session.commit()
        print("-" * 30)


def get_schpolldir_path(school: School, poll: Poll, sch_path: bool = False) -> str:
    school_dir = f"{school.abbr}{school.id}"
    poll_dir = f"{poll.id}"
    if sch_path:
        path = f"{os.getcwd()}/EduVoteFlow/static/DataStore/{school_dir}"
    else:
        path = f"{os.getcwd()}/EduVoteFlow/static/DataStore/{school_dir}/{poll_dir}"
    return path


sort_by_votes = lambda x: x["votes"]


def posttotal_votecasts(candidates: list) -> int:
    total = 0
    for candidate in candidates:
        total += candidate["votes"]
    return total


def candidates_percent(votes_casted: int, candidate: dict):
    candidate_votes = candidate["votes"]
    percentage = 0
    if candidate_votes and votes_casted:
        percentage = round((candidate_votes / votes_casted) * 100, 1)
    candidate["percentage"] = percentage
    return candidate


def candidates_rank(ele_dict: dict):
    res = {}
    winners = []
    losers = []
    for post in ele_dict.keys():
        sorted_candidates = sorted(ele_dict[post], key=sort_by_votes, reverse=True)
        votes_casted = posttotal_votecasts(sorted_candidates)
        sorted_candidates = [
            candidates_percent(votes_casted, c) for c in sorted_candidates
        ]
        if post not in res:
            res[post] = {
                "votes_casted": votes_casted,
                "winner_votes": 0,
                "winners": [],
                "losers": [],
                "any_tie": False,
                "any_voted": True,
            }
        res_post = res[post]
        for idx, cand in enumerate(sorted_candidates):
            # if all candidates have zero votes
            if idx == 0 and cand["votes"] == 0:
                res[post]["any_voted"] = False
                res[post]["losers"].extend(sorted_candidates)
                losers.extend(sorted_candidates)
                break
            # if muiltple candidates have the same max votes
            elif res_post["winners"] and cand["votes"] == res_post["winner_votes"]:
                res[post]["winners"].append(cand)
                if not res_post["any_tie"]:
                    res[post]["any_tie"] = True
            # if thr current candidate is already a loser
            elif res_post["winners"] and cand["votes"] < res_post["winner_votes"]:
                res[post]["losers"].extend(sorted_candidates[idx:])
                losers.extend(sorted_candidates[idx:])
                break
            else:
                res[post]["winners"].append(cand)
                if res_post["winner_votes"] == 0:
                    res[post]["winner_votes"] = cand["votes"]
        if not res[post]["any_tie"]:
            winners.extend(res[post]["winners"])
    return {"winners": winners, "losers": losers, "res_obj": res}


test_dict = {
    "p1": [
        {
            "id": 1,
            "full_name": "John Doe",
            "post": "p1",
            "house": "H1",
            "gender": "Male",
            "logo": "",
            "slogan": "Hello World!",
            "votes": 0,
        },
        {
            "id": 2,
            "full_name": "Jane Smith",
            "post": "p1",
            "house": "H2",
            "gender": "Female",
            "logo": "",
            "slogan": "Goodbye World!",
            "votes": 2,
        },
        {
            "id": 3,
            "full_name": "Bob Johnson",
            "post": "p1",
            "house": "H3",
            "gender": "Male",
            "logo": "",
            "slogan": "Hello Again!",
            "votes": 1,
        },
    ],
    "p2": [
        {
            "id": 4,
            "full_name": "Noah Johnson",
            "post": "p2",
            "house": "H1",
            "gender": "Male",
            "logo": "",
            "slogan": "Hello Again and !",
            "votes": 2,
        },
        {
            "id": 5,
            "full_name": "Tech Tim",
            "post": "p2",
            "house": "H3",
            "gender": "Male",
            "logo": "",
            "slogan": "Hello Again noomm!",
            "votes": 9,
        },
    ],
    "p3": [
        {
            "id": 6,
            "full_name": "Tristar Mosh",
            "post": "p3",
            "house": "H3",
            "gender": "Male",
            "logo": "",
            "slogan": "Hello Again noomm!",
            "votes": 2,
        },
        {
            "id": 7,
            "full_name": "Tech Mosh",
            "post": "p3",
            "house": "H2",
            "gender": "Male",
            "logo": "",
            "slogan": "Hello Again noomm!",
            "votes": 5,
        },
        {
            "id": 8,
            "full_name": "Moxie Tim",
            "post": "p3",
            "house": "H3",
            "gender": "FeMale",
            "logo": "",
            "slogan": "Hello Tick!",
            "votes": 1,
        },
        {
            "id": 9,
            "full_name": "John Felt",
            "post": "p3",
            "house": "H1",
            "gender": "Male",
            "logo": "",
            "slogan": "Hello Again noomm!",
            "votes": 5,
        },
    ],
    "p4": [
        {
            "id": 6,
            "full_name": "Tristar Mosh",
            "post": "p3",
            "house": "H3",
            "gender": "Male",
            "logo": "",
            "slogan": "Hello Again noomm!",
            "votes": 0,
        },
        {
            "id": 7,
            "full_name": "Tech Mosh",
            "post": "p3",
            "house": "H2",
            "gender": "Male",
            "logo": "",
            "slogan": "Hello Again noomm!",
            "votes": 0,
        },
    ],
}
