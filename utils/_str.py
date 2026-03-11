def clean_underscores_front_back(text: str) -> str:
    """Entfernt führende und folgende Unterstriche von einem String."""
    if not text:
        return text
    return text.strip("_")



def rm_prev_mark(text):
    is_prev_pre = text.startswith("prev_")
    is_prev_after = text.endswith("_prev")
    if is_prev_pre:
        pid = text.replace("prev_", "").strip()
    elif is_prev_after:
        pid = text.replace("_prev", "").strip()
    else:
        pid = text
    return pid