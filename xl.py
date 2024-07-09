import openpyxl

# Create a new Excel file
wb = openpyxl.Workbook()

# Select the first sheet
sheet = wb["Sheet"]

# Set the header row
sheet["A1"] = "student_name"
sheet["B1"] = "house"
sheet["C1"] = "party"
sheet["D1"] = "gender"
sheet["E1"] = "slogan"
sheet["F1"] = "post"

# Add data to the sheet using tuples
data = [
    ("John Doe", "H1", "Party A", "Male", "Hello World!", "p1"),
    ("Jane Smith", "H2", "Party B", "Female", "Goodbye World!", "p2"),
    ("Bob Johnson", "H3", "Party A", "Male", "Hello Again!", "p1"),
]

for row in data:
    sheet.append(row)

# Save the file
wb.save("/mnt/sdcard/example.xlsx")
# wb.s
# av()
