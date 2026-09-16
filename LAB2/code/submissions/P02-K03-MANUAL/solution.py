"""Implement kata-03: Rotacao de matriz quadrada."""


def solve(value):
    if not isinstance(value, dict):
        raise ValueError("entrada deve ser um objeto")

    if "grid" not in value or "turns" not in value:
        raise ValueError("grid e turns sao obrigatorios")

    grid = value["grid"]
    turns = value["turns"]

    if not isinstance(turns, int) or isinstance(turns, bool):
        raise ValueError("turns deve ser um inteiro")

    if not isinstance(grid, list):
        raise ValueError("grid deve ser uma lista")

    n = len(grid)
    if n == 0:
        raise ValueError("grid nao pode ser vazia")

    for row in grid:
        if not isinstance(row, list) or len(row) != n:
            raise ValueError("grid deve ser uma matriz quadrada")
        for elem in row:
            if isinstance(elem, bool) or not isinstance(elem, (int, float, str)):
                raise ValueError("elementos da grid invalidos")

    effective_turns = turns % 4

    res = grid
    for _ in range(effective_turns):
        res = [list(row) for row in zip(*res[::-1])]

    return res