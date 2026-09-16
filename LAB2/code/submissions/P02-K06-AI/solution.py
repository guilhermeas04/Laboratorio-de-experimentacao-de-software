"""Trial P02-K06-AI: contagem de picos com plato."""


def _groups(values):
    grouped = []
    for value in values:
        if grouped and grouped[-1] == value:
            continue
        grouped.append(value)
    return grouped


def solve(value):
    if not isinstance(value, dict):
        raise ValueError("entrada deve ser um objeto")

    values = value.get("values")
    if not isinstance(values, list):
        raise ValueError("values deve ser uma lista")
    if any(
        not isinstance(item, (int, float)) or isinstance(item, bool) for item in values
    ):
        raise ValueError("values deve conter apenas numeros")

    compacted = _groups(values)
    total = 0
    for index in range(1, len(compacted) - 1):
        if compacted[index - 1] < compacted[index] > compacted[index + 1]:
            total += 1
    return total
