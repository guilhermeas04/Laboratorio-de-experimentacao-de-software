"""Trial P01-K05-MANUAL: primeira janela livre na agenda."""


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
        or window[0] >= window[1]
    ):
        raise ValueError("window invalida")
    if not isinstance(duration, int) or isinstance(duration, bool) or duration <= 0:
        raise ValueError("duration invalida")

    window_start, window_end = window
    occupied = []
    for interval in busy:
        if (
            not isinstance(interval, list)
            or len(interval) != 2
            or not isinstance(interval[0], int)
            or not isinstance(interval[1], int)
        ):
            raise ValueError("intervalo ocupado invalido")
        start, end = interval
        if start >= end or start < window_start or end > window_end:
            raise ValueError("intervalo ocupado fora da janela")
        occupied.append([start, end])

    occupied.sort(key=lambda item: item[0])

    cursor = window_start
    previous_end = window_start
    for start, end in occupied:
        if start < previous_end:
            raise ValueError("intervalos ocupados sobrepostos")
        if start - cursor >= duration:
            return [cursor, cursor + duration]
        cursor = end
        previous_end = end

    if window_end - cursor >= duration:
        return [cursor, cursor + duration]
    raise ValueError("sem janela livre")
