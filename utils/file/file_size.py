import os


def get_file_size(file_path):
    """Get the size of a file in bytes, KB, or MB."""
    try:
        file_size = os.path.getsize(file_path)
        if file_size < 1024:
            return f"{file_size} bytes"
        elif file_size < 1024 ** 2:
            return f"{file_size / 1024:.2f} KB"
        else:
            return f"{file_size / (1024 ** 2):.2f} MB"
    except FileNotFoundError:
        return "File not found."
    except Exception as e:
        return f"Error: {e}"


# Path to your file
file_path = r"C:\Users\wired\Downloads\cells_data (1).json"

# Get and print the file size
print(f"File size: {get_file_size(file_path)}")