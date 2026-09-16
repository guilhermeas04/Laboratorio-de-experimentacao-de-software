"""Trial P03-K03-MANUAL: rotação de matriz."""


def solve(value):
    if not isinstance(value, dict):
        raise ValueError("entrada deve ser um objeto")

    grid = value.get("grid")
    turns = value.get("turns")

    if not isinstance(grid, list) or not grid:
        raise ValueError("grid deve ser uma matriz não vazia")

    if not all(isinstance(row, list) for row in grid):
        raise ValueError("grid deve ser uma matriz")

    size = len(grid)

    if any(len(row) != size for row in grid):
        raise ValueError("grid deve ser quadrada")

    if not isinstance(turns, int):
        raise ValueError("turns deve ser um inteiro")

    turns = turns % 4

    result = grid

    for _ in range(turns):
        result = [list(row) for row in zip(*result[::-1])]

    return result