import chardet
from pygments import highlight
from pygments.lexers import SqlLexer
from pygments.formatters import TerminalFormatter

class SqlViewer:
    """
    pip install pygments chardet
-

    """

    def __init__(self):
        pass

    def main(self, file_path):

        try:
            # Detect file encoding
            with open(file_path, "rb") as raw_file:
                raw_data = raw_file.read(4096)
                detected_encoding = chardet.detect(raw_data)["encoding"]

            print(f"Detected file encoding: {detected_encoding}")

            # Read the file with the detected encoding
            with open(file_path, "r", encoding=detected_encoding) as file:
                sql_content = file.read()

            # Highlight SQL
            formatted_sql = highlight(sql_content, SqlLexer(), TerminalFormatter())
            print(formatted_sql)

        except UnicodeDecodeError as e:
            print(f"Error decoding file: {e}")
        except Exception as e:
            print(f"An unexpected error occurred: {e}")

file_path= r"C:\Users\wired\OneDrive\Desktop\Projects\pythonProject\data\raw\reactome\current.sql"

if __name__ == "__main__":
    SqlViewer().main(file_path)