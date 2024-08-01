# imports
from functools import wraps
from flask import (
    abort,
    json,
    render_template,
    request,
    Blueprint,
    flash,
    redirect,
    url_for,
    jsonify,
    current_app,
    session,
)
from application.models import School, Poll, Student, Candidate
from application.election.forms import StudentLogin
from flask_login import login_required, current_user
from sqlalchemy import func
from application import db
from application.auth.utils import studentloginrequired
from application.polls.utils import get_opposed_candidates
from .utils import prepare_candidates

# Register this Page as a Blueprint
election = Blueprint("election", __name__)
# Simple Decorator to check for active polls only


def activepollrequired(func):
    @wraps(func)
    def func_wrapper(school_id, poll_id, *args):
        poll = Poll.query.get(int(poll_id))
        if not poll:
            abort(404)
        elif poll.status == "Active":
            return func(school_id, poll_id, *args)
        else:
            return render_template("election/not-active.html", poll_name=poll.name)

    return func_wrapper


@election.route("/cast-vote", methods=["POST"])
# @login_required
@studentloginrequired
@activepollrequired
def cast_vote(school_id, poll_id):
    candidate_id = int(json.loads(request.data)["candidateId"])
    print(candidate_id, poll_id)
    candidate = Candidate.query.filter_by(poll_id=poll_id, id=candidate_id).first()
    poll = Poll.query.get(int(poll_id))
    print(candidate, "*" * 20)
    if candidate and poll:
        candidate.votes += 1
        poll.total_votes += 1
        db.session.commit()
    return jsonify({})


@election.route("/")
@login_required
# @activepollrequired
def splash_screen(school_id, poll_id):
    school = School.query.get(school_id)
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    if not poll:
        abort(404)
    if poll.status != "Active":
        return render_template("election/not-started.html")
    link = url_for("auth.student_login", school_id=school.id, poll_id=poll.id)
    return render_template(
        "election/splashscreen.html",
        title="Election",
        school=school,
        poll=poll,
        link=link,
    )


@election.route("/votingpage/", methods=["GET", "POST"])
# @login_required
@studentloginrequired
@activepollrequired
def voting_page(school_id, poll_id):
    school = School.query.get(school_id)
    current_student = current_user
    if not school:
        abort(404)
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    if not poll:
        abort(404)
    candidates = get_opposed_candidates(poll.id, school.id).all()

    # if request.method == "POST":
    #     candidate_id = request.form.get("")
    #     # cast_vote(, poll_id)
    #     return redirect(
    #         url_for(
    #             "election.student_logout",
    #             poll_id=poll_id,
    #             s_id=s_id,
    #         )
    #     )

    print("OPPOSED", candidates)
    applicable_candidates = prepare_candidates(candidates)
    with open("test.py", "w") as f:
        f.write("d = " + str(applicable_candidates))

    print("PREPARED", applicable_candidates)
    return render_template(
        "election/voting.html",
        title="Election",
        school=school,
        poll=poll,
        student=current_student,
        candidates=json.dumps(applicable_candidates),
    )


@election.route("/get_candidate_data/<id>")
def get_candidate_data(school_id, poll_id, id):
    candidate = Candidate.query.filter_by(poll_id=poll_id, id=id).first()
    if candidate:
        url = (
            url_for("static", filename=f"media/{school_abbr}/{poll_id}/")
            + candidate.logo
        )
        print(url)
        return jsonify({"logo_url": url, "slogan": candidate.slogan})
    return abort(404)
