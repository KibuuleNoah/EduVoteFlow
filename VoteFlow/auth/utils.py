# import subprocess
# import time
# from PIL import Image
# from resizeimage import resizeimage
#
# def img2svg(filename):
# 	start = time.time()
# 	try:
# 		#Perform Vectorization
# 		url = "https://www.vectorizer.io/api/v2/vectorize"
# 		cmd = f"""curl $ curl --http1.1 -H 'Expect:' --data-binary "@{filename}" "{url}" > {filename.split('.')[0]}.svg """
# 		out = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE).stdout.read()
# 		print(f"Completed In: {int(time.time() - start)}s")
# 		return {'status': 200, 'svg': f"{filename.split('.')[0]}.svg"}
# 	except Exception as e:
# 		return {'status': 500, 'errcode': str(e)}

from functools import wraps
from flask import abort
from flask_login import current_user, login_required

from VoteFlow.models import School, Student


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
