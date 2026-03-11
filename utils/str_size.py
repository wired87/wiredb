
def get_str_size(json_str:str):
    # Konvertierung in String und Messung der Bytes
    bytes_size = len(json_str.encode('utf-8'))
    mb_size = bytes_size / (1024 * 1024)

    print(f"Größe (geschätzt): {mb_size:.4f} MB")