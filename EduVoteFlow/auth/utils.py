from functools import wraps
from flask import abort
from flask_login import current_user, login_required
from flask_wtf.csrf import os
from werkzeug.utils import secure_filename

from EduVoteFlow.models import School, Student


# makes sure that the loggedin
# user is a student to access a given route
def studentloginrequired(func):
    @wraps(func)
    # user must be loggedin to processed
    @login_required
    def func_wrapper(*args, **kwargs):
        if not isinstance(current_user, Student):
            abort(401)
        return func(*args, **kwargs)

    return func_wrapper


# makes sure that the loggedin
# user is a school admin to access a given route
def schoolloginrequired(func):
    @wraps(func)
    # user must be loggedin to processed
    @login_required
    def func_wrapper(*args, **kwargs):
        if not isinstance(current_user, School):
            abort(401)
        return func(*args, **kwargs)

    return func_wrapper


def abbr_str(text: str) -> str:
    """
    Creates an abbreviation of given text

    :param text : string to be abbreviated
    :type text : str
    :returns : an abbreviated uppercase string
    :rtype : str
    """
    return "".join([t[0] for t in text.split()]).upper()


def get_file_extension(file_name: str | None) -> str:
    """
    Extracts an extension from a given file name

    :param file_name : where the extension is got
    :type : str
    :returns : file extension if found else empty string
    :rtype : str
    """
    if not file_name:
        return ""
    ext = os.path.splitext(secure_filename(file_name))[1]
    return ext
