from flask import render_template
from application import create_app

app = create_app()


@app.errorhandler(404)
def page_not_found(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(401)
def unauthorized(e):
    return render_template("errors/401.html"), 401


# if __name__ == "__main__":
# app.run(debug=True)
# app.run(host='0.0.0.0', port=80, debug=True)
# serve(app, host='0.0.0.0', port=80)
