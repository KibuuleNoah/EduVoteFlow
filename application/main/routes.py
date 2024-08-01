# imports
from flask import jsonify, render_template, request, Blueprint
from flask_login import login_required

# from application.models import SchoolUser, Poll
from application import db

# Register this Page as a Blueprint
main = Blueprint("main", __name__)


@main.route("/")
def splash_screen():
    return render_template("splashscreen.html", title="EduVoteFlow")


@main.route("/about")
def about():
    return "VOTEFLOW ABOUT PAGE"


@main.route("/nochrome")
def nochrome():
    return render_template("nochrome.html")
