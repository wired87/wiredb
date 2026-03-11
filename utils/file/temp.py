import os
import shutil
import tempfile





def write_temp_file(fiel_type, content):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=fiel_type)
    temp.write(content)
    temp.flush()


def rm_tmp(temp_dir_path):
    shutil.rmtree(temp_dir_path)
    print(f"removed {temp_dir_path}")



def write_tmp_local(tempdir_path, target_dir):
    os.makedirs(target_dir, exist_ok=True)

    print(f"write {tempdir_path} to {target_dir}")

    for root, dirs, files in os.walk(tempdir_path):
        for file in files:
            abs_path = os.path.join(root, file)
            rel_path = os.path.relpath(abs_path, tempdir_path)
            dest_path = os.path.join(target_dir, rel_path)

            # Zielordner erzeugen, falls nötig
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            # Datei kopieren
            shutil.copy2(abs_path, dest_path)
    rm_tmp(tempdir_path)