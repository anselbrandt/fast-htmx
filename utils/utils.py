import random

from .fruits import fruits
from .names import names


def fruitname():
    fruit_name = f"{random.choice(names)} {random.choice(fruits)}"
    return fruit_name.lower().replace(" ", "_")
