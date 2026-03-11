"""

smpel scale up a 3d list [1,[2,3],4] to [[1,2,4], [1,3,4]
programatically and modlar with np -> convert to list valid for any emelemt datatypes e.g. [(1,2), [(3,4),(5,6)],(7,7)]

"""

def expand_structure(struct):
    # 1. Identifiziere die maximale Länge aller Listen im Baum
    # (In deinem Beispiel: C hat len 5, also max_len = 5)
    max_len = 1
    for item in struct:
        if isinstance(item, list):
            max_len = max(max_len, len(item))

    # 2. Erstelle die Variationen
    expanded_results = []
    for i in range(max_len):
        variation = []
        for item in struct:
            if isinstance(item, list):
                # Nimm den Eintrag am aktuellen Index i.
                # Falls die Liste kürzer ist als max_len, nimm das letzte Element (Padding)
                val = item[i] if i < len(item) else item[-1]
                variation.append(val)
            else:
                # Einzelwerte (keine Liste) bleiben in JEDER Variation gleich
                variation.append(item)
        expanded_results.append(variation)

    return expanded_results


