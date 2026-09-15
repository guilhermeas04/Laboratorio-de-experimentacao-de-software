"""Trial P01-K02-MANUAL: primeiro caractere unico."""


def solve(value):
    if not isinstance(value, dict):
        raise ValueError("entrada deve ser um objeto")

    text = value.get("text")
    if not isinstance(text, str):
        raise ValueError("text deve ser uma string")

    counts = {}
    for char in text:
        if char in counts:
            counts[char] += 1
        else:
            counts[char] = 1

    index = 0
    for char in text:
        if counts[char] == 1:
            return index
        index += 1

    return -1
