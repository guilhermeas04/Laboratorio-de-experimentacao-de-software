def solve(value):
    if not isinstance(value, dict) or "values" not in value:
        raise ValueError("invalid input")
    values = value["values"]
    if not isinstance(values, list):
        raise ValueError("values must be a list")
    if any(
        not isinstance(item, (int, float)) or isinstance(item, bool)
        for item in values
    ):
        raise ValueError("values must be numeric")
    if len(values) < 3:
        return 0

    peaks = 0
    index = 1
    while index < len(values) - 1:
        if values[index] > values[index - 1]:
            end = index
            while end + 1 < len(values) and values[end + 1] == values[index]:
                end += 1
            if end < len(values) - 1 and values[end] > values[end + 1]:
                peaks += 1
            index = end
        index += 1
    return peaks