"""Implement kata-02: Primeiro caractere unico."""


def solve(value):
    if not isinstance(value, dict):
        raise ValueError("entrada deve ser um objeto")

    text = value.get("text")
    if not isinstance(text, str):
        raise ValueError("text deve ser uma string")

    freq = {}
    for char in text:
        freq[char] = freq.get(char, 0) + 1

    for idx, char in enumerate(text):
        if freq[char] == 1:
            return idx

    return -1