import os
betse_file_types = [".py", ".yaml", ".ipynb", ".lyx", ".md"]
def collect_all_files(root_dir, output_file):
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if file_path.endswith(tuple(betse_file_types)):
                    print("working path", file_path)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                            content = infile.read()
                            outfile.write(f"\n\n### Start of {file_path} ###\n\n")
                            outfile.write(content)
                            outfile.write(f"\n\n### End of {file_path} ###\n\n")
                    except Exception as e:
                        print(f"Failed to read {file_path}: {e}")

if __name__ == "__main__":
    root_folder = r"C:\Users\wired\OneDrive\Desktop\Projects\bm\_b\betse"
    output_file = r"C:\Users\wired\OneDrive\Desktop\Projects\bm\_b\betse_collection.txt"
    collect_all_files(root_folder, output_file)
    print("Done!")