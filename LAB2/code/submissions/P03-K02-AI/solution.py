from collections import Counter


def solve(value):
    if not isinstance(value, dict) or "text" not in value:
        raise ValueError("invalid input")
    text = value["text"]
    if not isinstance(text, str):
        raise ValueError("text must be a string")

    counts = Counter(text)
    for index, character in enumerate(text):
        if counts[character] == 1:
            return index
    return -1