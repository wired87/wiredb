import random
import string


def generate_id(
        length=20,
        mixed_dt=True  # numeric & alpha
):
    chars = string.ascii_letters
    if mixed_dt is True:
        chars += string.digits
    return ''.join(random.choices(chars, k=length)).lower()