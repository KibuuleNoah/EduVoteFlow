import openpyxl

# Create a new Excel file
wb = openpyxl.Workbook()

# Select the first sheet
sheet = wb["Sheet"]

# Set the header row
sheet["A1"] = "student_name"
sheet["B1"] = "house"
sheet["C1"] = "grade"
sheet["D1"] = "gender"
sheet["E1"] = "slogan"
sheet["F1"] = "post"

# Add data to the sheet using tuples
data = [
    ("John Doe", "H1", 11, "Male", "Hello World!", "p1"),
    ("Jane Smith", "H2", 7, "Female", "Goodbye World!", "p1"),
    ("Bob Johnson", "H3", 8, "Male", "Hello Again!", "p1"),
    ("Noah Johnson", "H1", 8, "Male", "Hello Again and !", "p2"),
    ("Tech Tim", "H3", 8, "female", "Hello Again noomm!", "p2"),
    ("Tristar Mosh", "H3", 8, "Male", "Hello Again noomm!", "p3"),
    ("Tech Mosh", "H2", 8, "Male", "Hello Again noomm!", "p3"),
    ("Moxie Tim", "H3", 8, "Female", "Hello Tick!", "p3"),
    ("John Felt", "H1", 8, "Male", "Hello Again noomm!", "p3"),
]

for row in data:
    sheet.append(row)

# Save the file
wb.save("/mnt/sdcard/example.xlsx")
# wb.s
# av()
