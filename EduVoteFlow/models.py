# Imports
from datetime import datetime
from flask import current_app
from EduVoteFlow import db, login_manager
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    print("USER_ID:", user_id)
    print("USER_QUERIED:", user_id)
    if not user:
        return None

    if user.user_type == "student":
        return Student.query.get(user.user_id)
    elif user.user_type == "school":
        return School.query.get(user.user_id)

    return None


class School(UserMixin, db.Model):
    __tablename__ = "schools"
    id = db.Column(db.Integer, primary_key=True)
    admin_username = db.Column(db.String, unique=True, nullable=False)
    name = db.Column(db.String, unique=True, nullable=False)
    abbr = db.Column(db.String, unique=True, nullable=False)
    email = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, unique=True, nullable=False)
    logo = db.Column(db.String, nullable=False)
    polls = db.relationship("Poll", backref="schools", cascade="all")

    def __repr__(self):
        return f"School('{self.name}', '{self.abbr}', '{self.admin_username}')"


class Student(UserMixin, db.Model):
    __tablename__ = "students"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    username = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    grade = db.Column(db.String, nullable=False)
    section = db.Column(db.String, nullable=False)
    roll_no = db.Column(db.String, nullable=False)
    gender = db.Column(db.String, nullable=False)
    house = db.Column(db.String, nullable=True)
    voted = db.Column(db.Boolean, default=False)
    flag = db.relationship(
        "FlaggedStudent", backref="students", cascade="all", lazy=True
    )
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id", ondelete="CASCADE"))
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id", ondelete="CASCADE"))

    def __repr__(self):
        return f"Student('{self.school_id}', '{self.name}')"


class Candidate(db.Model):
    __tablename__ = "candidates"
    id = db.Column(db.Integer, primary_key=True)
    names = db.Column(db.String, nullable=False)
    post = db.Column(db.String, nullable=False)
    house = db.Column(db.String, nullable=True)
    grade = db.Column(db.String, nullable=False)
    gender = db.Column(db.String, nullable=True)
    logo = db.Column(db.String, default="/static/media/default.jpg")
    slogan = db.Column(db.String, nullable=False)
    votes = db.Column(db.Integer, default=0)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id", ondelete="CASCADE"))
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id", ondelete="CASCADE"))

    @property
    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "post": self.post,
            "house": self.house,
            "gender": self.gender,
            "logo": self.logo,
            "slogan": self.slogan,
            "votes": self.votes,
        }


class Poll(db.Model):
    __tablename__ = "polls"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    # election_date = db.Column(db.String, nullable=False)
    houses = db.Column(db.PickleType, nullable=True)
    posts = db.Column(db.PickleType, nullable=False)
    year = db.Column(db.String, nullable=False)
    status = db.Column(db.String, nullable=False)
    total_votes = db.Column(db.Integer, default=0)
    total_voted = db.Column(db.Integer, default=0)
    students = db.relationship("Student", backref="polls", cascade="all")
    candidates = db.relationship("Candidate", backref="polls", cascade="all")
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id", ondelete="CASCADE"))

    def __repr__(self):
        return f"Poll('{self.name}', '{self.year}')"


class FlaggedStudent(db.Model):
    __tablename__ = "flaggedstudents"
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))
    poll_id = db.Column(db.Integer, db.ForeignKey("polls.id", ondelete="CASCADE"))
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id", ondelete="CASCADE"))


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String, nullable=False)
    user_id = db.Column(db.Integer, nullable=False)
