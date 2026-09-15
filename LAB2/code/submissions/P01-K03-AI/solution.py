"""Trial P01-K03-AI: rotacao de matriz quadrada."""


def _validate_grid(grid):
    if not isinstance(grid, list) or len(grid) == 0:
        raise ValueError("grid deve ser uma matriz quadrada nao vazia")

    size = len(grid)
    for row in grid:
        if not isinstance(row, list) or len(row) != size:
            raise ValueError("grid deve ser quadrada")


def _rotate_once(grid):
    size = len(grid)
    rotated = []
    for column in range(size):
        new_row = []
        for row in range(size - 1, -1, -1):
            new_row.append(grid[row][column])
        rotated.append(new_row)
    return rotated


def solve(value):
    if not isinstance(value, dict):
        raise ValueError("entrada deve ser um objeto")

    grid = value.get("grid")
    turns = value.get("turns")
    if not isinstance(turns, int) or isinstance(turns, bool):
        raise ValueError("turns deve ser inteiro")

    _validate_grid(grid)

    result = [row[:] for row in grid]
    for _ in range(turns % 4):
        result = _rotate_once(result)

    return result
