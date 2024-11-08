import random
import string
import math
import itertools


def generate_otp(length=6) -> str:
    otp = ""
    for _ in range(length):
        otp += str(random.choice(string.digits))
    return otp


def avatar_directory_path(instance, filename: str) -> str:
    file_format = filename.split(".", 1)[-1]
    return f"avatar/{instance.account.id}.{file_format}"


def mask_email(email: str) -> str:
    sub_strings = email.split("@", 1)
    id_len: int = max(math.floor(len(sub_strings[0]) / 3), 1)
    sub_strings[0] = sub_strings[0][0:id_len] + "".join(
        itertools.repeat("*", len(sub_strings[0]) - id_len)
    )
    return sub_strings[0] + "@" + sub_strings[1]
