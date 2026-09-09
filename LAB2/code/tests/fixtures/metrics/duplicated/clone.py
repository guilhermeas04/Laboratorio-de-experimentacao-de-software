def helper(items):
    total = 0
    for item in items:
        if item > 0:
            total += item
        elif item < 0:
            total -= item
        else:
            total += 1
    return total


def other_helper(items):
    total = 0
    for item in items:
        if item > 0:
            total += item
        elif item < 0:
            total -= item
        else:
            total += 1
    return total
