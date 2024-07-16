# imports
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
from VoteFlow.models import School, Poll, Student, Candidate
from VoteFlow.election.forms import StudentLogin
from flask_login import login_required, current_user
from VoteFlow import db
from VoteFlow.auth.utils import studentloginrequired

# Register this Page as a Blueprint
election = Blueprint("election", __name__)

# Simple Decorator to check for active polls only
# def activepollrequired(func):
# 	@wraps(func)
# 	def func_wrapper(school_abbr, poll_id):
# 		poll = Poll.query.filter_by(host=school_abbr, id=poll_id).first()
# 		if(poll.status == 'Active'):
# 			return func(school_abbr, poll_id)
# 		else:
# 			flash(f'The Poll ({poll.poll_name}) is currently not Active.', 'danger')
# 			return redirect(url_for('polls.home', school_abbr=school_abbr))
# 	return func_wrapper


def prepare_candidates(candidates: list[Candidate]):
    displayed_candidates = {}
    print(candidates)
    for candidate in candidates:
        dict_candidate = candidate.to_dict
        candidate_post = dict_candidate["post"]
        if candidate_post in displayed_candidates:
            displayed_candidates[candidate_post].append(dict_candidate)
        else:
            displayed_candidates[candidate_post] = [dict_candidate]
    return displayed_candidates


@election.route("/cast-vote", methods=["POST"])
@login_required
@studentloginrequired
def cast_vote(school_id, poll_id):
    candidate_id = int(json.loads(request.data)["candidateId"])
    print(candidate_id, poll_id)
    candidate = Candidate.query.filter_by(poll_id=poll_id, id=candidate_id).first()
    print(candidate, "*" * 20)
    if candidate:
        poll = Poll.query.get(int(poll_id))
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


@election.route("/votingpage/<s_id>", methods=["GET", "POST"])
# @login_required
@studentloginrequired
# @activepollrequired
def voting_page(school_id, poll_id, s_id):
    school = School.query.get(school_id)
    current_student = current_user
    if not school:
        abort(404)
    poll = Poll.query.filter_by(school_id=school.id, id=poll_id).first()
    if not poll:
        abort(404)
    candidates = poll.candidates

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

    applicable_candidates = prepare_candidates(candidates)

    print(applicable_candidates)
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
            url_for("static", filename=f"DataStore/{school_abbr}/{poll_id}/")
            + candidate.logo
        )
        print(url)
        return jsonify({"logo_url": url, "slogan": candidate.slogan})
    return abort(404)
