def extract_trailing_numbers(text):
    try:
        # 1. Prüfen, ob der String überhaupt mit einer Zahl endet
        if not text or not text[-1].isdigit():
            return ""  # Oder None, falls gewünscht

        # 2. Alle numerischen Zeichen vom Ende her sammeln
        result = []
        for char in reversed(text):
            if char.isdigit():
                result.append(char)
            else:
                # Sobald ein nicht-numerisches Zeichen kommt: Stop
                break

        # Liste umdrehen und zum String zusammenfügen
        return "".join(reversed(result))
    except Exception as e:
        print("Err extract_trailing_numbers", e)


