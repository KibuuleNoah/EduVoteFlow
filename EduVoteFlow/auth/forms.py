from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, FileField, BooleanField
from wtforms.validators import DataRequired, EqualTo, Email, ValidationError
from wtforms_components import ColorField

# Forms related to User Functionality i.e Logins, Register etc


class SchoolLogin(FlaskForm):
    admin_username = StringField("Admin Username", validators=[DataRequired()])
    school_abbr = StringField("School Abbr", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Login")


class SchoolRegister(FlaskForm):
    school_name = StringField("School Name", validators=[DataRequired()])
    school_abbr = StringField("School Abbreviation", validators=[DataRequired()])
    admin_username = StringField("Admin Username", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    school_logo = FileField()
    submit = SubmitField("Register")


class AddVoters(FlaskForm):
    file = FileField()
    submit = SubmitField("Add Voters")


class AddCandidates(FlaskForm):
    file = FileField()
    submit = SubmitField("Add Voters")
