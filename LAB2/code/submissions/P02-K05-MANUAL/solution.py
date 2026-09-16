"""Implement kata-05: Primeira janela livre na agenda."""


def solve(value):
    if not isinstance(value, dict):
        raise ValueError("entrada deve ser um objeto")

    busy = value.get("busy")
    window = value.get("window")
    duration = value.get("duration")

    if not isinstance(busy, list):
        raise ValueError("busy invalido")

    if (
        not isinstance(window, list)
        or len(window) != 2
        or not isinstance(window[0], int)
        or not isinstance(window[1], int)
        or isinstance(window[0], bool)
        or isinstance(window[1], bool)
        or window[0] >= window[1]
    ):
        raise ValueError("window invalida")

    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise ValueError("duration invalida")

    win_start, win_end = window
    intervals = []

    for item in busy:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not isinstance(item[0], int)
            or not isinstance(item[1], int)
            or isinstance(item[0], bool)
            or isinstance(item[1], bool)
        ):
            raise ValueError("intervalo ocupado invalido")

        start, end = item
        if start >= end or start < win_start or end > win_end:
            raise ValueError("intervalo ocupado fora da janela")

        intervals.append((start, end))

    intervals.sort(key=lambda x: x[0])

    curr_time = win_start
    for start, end in intervals:
        if start < curr_time:
            raise ValueError("intervalos ocupados sobrepostos")

        if start - curr_time >= duration:
            return [curr_time, curr_time + duration]

        curr_time = end

    if win_end - curr_time >= duration:
        return [curr_time, curr_time + duration]

    raise ValueError("sem janela livre")