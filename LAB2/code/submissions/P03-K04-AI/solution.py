def solve(value):
    if not isinstance(value, dict):
        raise ValueError("input must be an object")

    amount = value.get("amount")
    coins = value.get("coins")
    if (
        not isinstance(amount, int)
        or isinstance(amount, bool)
        or amount < 0
        or not isinstance(coins, list)
        or not coins
        or any(
            not isinstance(coin, int) or isinstance(coin, bool) or coin <= 0
            for coin in coins
        )
        or len(set(coins)) != len(coins)
    ):
        raise ValueError("invalid coin system")

    best = [None] * (amount + 1)
    best[0] = (0, (0,) * len(coins))
    for current in range(1, amount + 1):
        for index, coin in enumerate(coins):
            if coin > current or best[current - coin] is None:
                continue
            previous_count, previous_vector = best[current - coin]
            vector = list(previous_vector)
            vector[index] += 1
            candidate = (previous_count + 1, tuple(vector))
            if best[current] is None or candidate < best[current]:
                best[current] = candidate

    if best[amount] is None:
        raise ValueError("amount cannot be represented")
    return list(best[amount][1])