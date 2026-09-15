"""Trial P01-K04-MANUAL: troco com menor quantidade de moedas."""


def solve(value):
    if not isinstance(value, dict):
        raise ValueError("entrada deve ser um objeto")

    amount = value.get("amount")
    coins = value.get("coins")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
        raise ValueError("amount invalido")
    if not isinstance(coins, list) or len(coins) == 0:
        raise ValueError("coins invalido")

    seen = set()
    for coin in coins:
        if not isinstance(coin, int) or isinstance(coin, bool) or coin <= 0:
            raise ValueError("coin invalida")
        if coin in seen:
            raise ValueError("coin repetida")
        seen.add(coin)

    best = [None] * (amount + 1)
    best[0] = [0 for _ in coins]

    current_amount = 1
    while current_amount <= amount:
        candidate = None
        coin_index = 0
        while coin_index < len(coins):
            coin = coins[coin_index]
            previous = current_amount - coin
            if previous >= 0 and best[previous] is not None:
                attempt = best[previous][:]
                attempt[coin_index] += 1
                if candidate is None:
                    candidate = attempt
                else:
                    attempt_count = sum(attempt)
                    candidate_count = sum(candidate)
                    if attempt_count < candidate_count:
                        candidate = attempt
                    elif attempt_count == candidate_count and attempt < candidate:
                        candidate = attempt
            coin_index += 1
        best[current_amount] = candidate
        current_amount += 1

    if best[amount] is None:
        raise ValueError("sem combinacao")
    return best[amount]
