import os


def save_img_bytes_local_as_str(base_dest, byte_data_store:dict):
    for k, v in byte_data_store.items():
        save_path = os.path.join(f"{base_dest}", f"{k}.txt")
        with open(save_path, "w") as f:
            f.write(v)