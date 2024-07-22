import io
import zipfile


def is_excel_file(file_bytes):
    try:
        # Check for ZIP file signature
        if file_bytes[:2] != b"PK":
            return False

        # Use the bytes as a file-like object
        with zipfile.ZipFile(io.BytesIO(file_bytes)) as zip_file:
            # Check for specific files within the ZIP archive
            if "xl/workbook.xml" in zip_file.namelist():
                return True
    except Exception as e:
        # Handle exceptions if the bytes are not a valid ZIP file or other issues
        return False

    return False


# Example usage
with open("path_to_your_file.xlsx", "rb") as f:
    file_bytes = f.read()

if is_excel_file(file_bytes):
    print("The file is an Excel file.")
else:
    print("The file is not an Excel file.")
