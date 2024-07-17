from EduVoteFlow import create_app, db
from EduVoteFlow.models import Poll, Student, FlaggedStudent, Candidate
import pprint

app = create_app()
with app.app_context():
    students = Student.query.all()
    flaggedstudents = FlaggedStudent.query.all()
    polls = Poll.query.all()
    candidates = Candidate.query.all()
    [db.session.delete(s) for s in students]
    [db.session.delete(f) for f in flaggedstudents]
    # [db.session.delete(j) for j in polls]
    [db.session.delete(n) for n in candidates]
    # xpoll = polls[0]
    # print(xpoll.poll_name)
    # pos = xpoll.posts
    # pprint.pprint(pos)
    db.session.commit()
