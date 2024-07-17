from flask_wtf import FlaskForm
from wtforms import (
    StringField,
    SubmitField,
    PasswordField,
    FileField,
    BooleanField,
    TextAreaField,
    SelectField,
    IntegerField,
)
from wtforms.validators import (
    DataRequired,
    Length,
    EqualTo,
    Email,
    ValidationError,
    Optional,
)
from wtforms_components import ColorField

# from flask_wtf import FlaskForm
# from wtforms import StringField, PasswordField, IntegerField, BooleanField, SelectField, SubmitField
# from wtforms.validators import DataRequired, Length, Optional
#


# Forms related to User Functionality i.e Logins, Register etc


class EditFlaggedUsernameForm(FlaskForm):
    submit = SubmitField("Update Usernames")


class CreatePollForm(FlaskForm):
    name = StringField("Poll Name", validators=[DataRequired()])
    houses = TextAreaField("Houses")
    posts = TextAreaField("posts", validators=[DataRequired()])
    year = StringField("Year", validators=[DataRequired()])
    submit = SubmitField("Create Poll")


class AddStudentsForm(FlaskForm):
    students = FileField()
    submit = SubmitField("Upload DataFile")


class AddCandidatesForm(FlaskForm):
    candidates = FileField()
    candidates_logo = FileField()
    submit = SubmitField("Upload Data")


class AddStudentForm(FlaskForm):
    student_name = StringField(
        "Student Name", validators=[DataRequired(), Length(min=2, max=100)]
    )
    grade = IntegerField("Grade", validators=[DataRequired()])
    section = StringField("Section", validators=[DataRequired(), Length(min=1, max=10)])
    roll_no = StringField(
        "Roll Number", validators=[DataRequired(), Length(min=1, max=20)]
    )
    gender = SelectField(
        "Gender",
        choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
        validators=[Optional()],
    )
    house = StringField("House", validators=[Optional(), Length(max=50)])
    submit = SubmitField("Add")


class AddCandidateForm(FlaskForm):
    candidate_name = StringField(
        "Candidate Name", validators=[DataRequired(), Length(min=2, max=100)]
    )
    post = StringField("Post", validators=[DataRequired(), Length(min=2, max=50)])
    house = StringField("House", validators=[Optional(), Length(max=50)])
    party = StringField("Party", validators=[Optional(), Length(max=50)])
    gender = SelectField(
        "Gender",
        choices=[("Male", "Male"), ("Female", "Female"), ("Other", "Other")],
        validators=[Optional()],
    )
    logo = FileField("Logo", validators=[Optional()])
    slogan = StringField("Slogan", validators=[DataRequired(), Length(min=2, max=200)])
    submit = SubmitField("Add")
