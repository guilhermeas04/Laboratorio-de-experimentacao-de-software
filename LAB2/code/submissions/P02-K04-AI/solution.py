"""Trial P02-K04-AI: troco com menor quantidade de moedas."""


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

    for current in range(1, amount + 1):
        candidate = None
        for index, coin in enumerate(coins):
            previous = current - coin
            if previous < 0 or best[previous] is None:
                continue
            attempt = best[previous][:]
            attempt[index] += 1
            if candidate is None:
                candidate = attempt
                continue
            attempt_total = sum(attempt)
            candidate_total = sum(candidate)
            if attempt_total < candidate_total:
                candidate = attempt
            elif attempt_total == candidate_total and attempt < candidate:
                candidate = attempt
        best[current] = candidate

    if best[amount] is None:
        raise ValueError("sem combinacao")
    return best[amount]
