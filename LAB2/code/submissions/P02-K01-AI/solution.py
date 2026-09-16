"""Trial P02-K01-AI: intervalos consolidados."""


def solve(value):
    if not isinstance(value, dict):
        raise ValueError("entrada deve ser um objeto")

    intervals = value.get("intervals")
    if not isinstance(intervals, list):
        raise ValueError("intervals deve ser uma lista")

    ordered = []
    for item in intervals:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], int)
            or not isinstance(item[1], int)
            or isinstance(item[0], bool)
            or isinstance(item[1], bool)
        ):
            raise ValueError("intervalo invalido")

        start, end = item
        if start > end:
            raise ValueError("inicio maior que fim")
        ordered.append([start, end])

    ordered.sort(key=lambda pair: pair[0])

    merged = []
    for current_start, current_end in ordered:
        if not merged:
            merged.append([current_start, current_end])
            continue

        last = merged[-1]
        if current_start <= last[1]:
            if current_end > last[1]:
                last[1] = current_end
        else:
            merged.append([current_start, current_end])

    return merged
