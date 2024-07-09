from VoteFlow.models import Student
from openpyxl import load_workbook


def extract_excel_data(fileobject):
    wb = load_workbook(fileobject, data_only=True)
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    data = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        data_object = {
            headers[i]: (row[i] if row[i] is not None else "")
            for i in range(len(headers))
        }
        data.append(data_object)
    print(headers)
    print(data)
    return data


def create_username(fullname, grade, section):
    subnames = fullname.strip().split(" ")
    print(subnames)
    firstname = subnames[0]
    username = ""
    # CHECK FOR SINGLE LETTER FIRST NAME
    if len(firstname) > 2:
        username = "{0}{1}{2}".format(firstname, grade, section)
    else:
        username = "{0}{1}{2}".format(subnames[1], grade, section)
    return username


# Check For Duplocate usernames and report them.
def flag_duplicate_usernames(data):
    # CODE TO GET INDEX OF DUPLICATE NAMES
    def list_duplicates_of(seq, item):
        start_at = -1
        locs = []
        while True:
            try:
                loc = seq.index(item, start_at + 1)
            except ValueError:
                break
            else:
                locs.append(loc)
                start_at = loc
        return locs

    # GET INDEX OF DUPLICATES
    usernames = [data[x]["username"] for x in range(len(data))]
    all_indexes = [list_duplicates_of(usernames, u) for u in usernames]

    # REMOVING DUPLICATE INDEXES
    duplicateIndexes = []
    for d in all_indexes:
        if len(d) > 1:
            if d not in duplicateIndexes:
                duplicateIndexes.append(d)
    # GET DUPLICATE ITEMS FROM INDEXES
    duplicatedObjects = []
    for e in duplicateIndexes:
        for index in e:
            duplicatedObjects.append(data[index])

    # SEND BACK DB OBJECTS
    student_objects = []
    for i in range(len(duplicatedObjects)):
        student = Student.query.filter_by(
            id=int(duplicatedObjects[i]["id"]), roll_no=duplicatedObjects[i]["roll_no"]
        ).first()
        student_objects.append(student)
    return student_objects
