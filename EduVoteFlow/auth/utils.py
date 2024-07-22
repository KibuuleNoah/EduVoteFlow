from functools import wraps
from flask import abort
from flask_login import current_user, login_required
from flask_wtf.csrf import os
from werkzeug.utils import secure_filename

from EduVoteFlow.models import School, Student


def studentloginrequired(func):
    @wraps(func)
    @login_required
    def func_wrapper(*args, **kwargs):
        if not isinstance(current_user, Student):
            abort(401)
        return func(*args, **kwargs)

    return func_wrapper


def schoolloginrequired(func):
    @wraps(func)
    @login_required
    def func_wrapper(*args, **kwargs):
        if not isinstance(current_user, School):
            abort(401)
        return func(*args, **kwargs)

    return func_wrapper


def abbr_str(text: str) -> str:
    return "".join([t[0] for t in text.split()]).upper()


def get_img_extension(img_name: str | None) -> str:
    if not img_name:
        return ""
    ext = os.path.splitext(secure_filename(img_name))[1]
    print("EXT", ext)
    return ext
