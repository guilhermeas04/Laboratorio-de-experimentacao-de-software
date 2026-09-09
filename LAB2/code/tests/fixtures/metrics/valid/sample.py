def score(values):
    total = 0
    for value in values:
        if value > 0:
            total += value
        elif value < 0:
            total -= value
        else:
            total += 1
    return total


def classify(value):
    if value > 10:
        return "high"
    if value > 5:
        return "mid"
    return "low"
