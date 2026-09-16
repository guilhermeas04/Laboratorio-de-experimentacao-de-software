def solve(value):
    if not isinstance(value, dict):
        raise ValueError("input must be an object")

    busy = value.get("busy")
    window = value.get("window")
    duration = value.get("duration")
    if (
        not isinstance(busy, list)
        or not isinstance(window, list)
        or len(window) != 2
        or not all(isinstance(item, int) and not isinstance(item, bool) for item in window)
        or window[0] >= window[1]
        or not isinstance(duration, int)
        or isinstance(duration, bool)
        or duration <= 0
    ):
        raise ValueError("invalid schedule")

    intervals = []
    for interval in busy:
        if (
            not isinstance(interval, list)
            or len(interval) != 2
            or not all(isinstance(item, int) and not isinstance(item, bool) for item in interval)
            or interval[0] >= interval[1]
            or interval[0] < window[0]
            or interval[1] > window[1]
        ):
            raise ValueError("invalid busy interval")
        intervals.append(interval)

    intervals.sort(key=lambda interval: interval[0])
    previous_end = window[0]
    for start, end in intervals:
        if start < previous_end:
            raise ValueError("overlapping busy intervals")
        if start - previous_end >= duration:
            return [previous_end, previous_end + duration]
        previous_end = end

    if window[1] - previous_end >= duration:
        return [previous_end, previous_end + duration]
    raise ValueError("no available window")