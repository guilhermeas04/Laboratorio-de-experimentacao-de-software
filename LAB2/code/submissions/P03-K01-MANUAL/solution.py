def solve(value):
    if not isinstance(value, dict) or "intervals" not in value:
        raise ValueError("invalid input")
    intervals = value["intervals"]
    if not isinstance(intervals, list):
        raise ValueError("intervals must be a list")

    ordered = []
    for interval in intervals:
        if (
            not isinstance(interval, list)
            or len(interval) != 2
            or any(not isinstance(item, int) or isinstance(item, bool) for item in interval)
            or interval[0] > interval[1]
        ):
            raise ValueError("invalid interval")
        ordered.append(interval)

    ordered.sort(key=lambda interval: interval[0])
    merged = []
    for start, end in ordered:
        if not merged or start > merged[-1][1] + 1:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return merged