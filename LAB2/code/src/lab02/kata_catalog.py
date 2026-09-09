"""Frozen acceptance catalog for exactly six locally authored katas."""

from __future__ import annotations

from .kata_contract import AcceptanceCase, KataDefinition


KATAS: tuple[KataDefinition, ...] = (
    KataDefinition(
        "kata-01",
        "Intervalos consolidados",
        (
            AcceptanceCase("caso_normal", {"intervals": [[1, 3], [2, 6], [8, 10]]}, [[1, 6], [8, 10]]),
            AcceptanceCase("intervalos_adjacentes", {"intervals": [[1, 2], [2, 4]]}, [[1, 4]]),
            AcceptanceCase("lista_vazia", {"intervals": []}, []),
            AcceptanceCase("ordem_de_entrada", {"intervals": [[9, 11], [1, 2], [2, 5]]}, [[1, 5], [9, 11]]),
            AcceptanceCase("fim_menor_que_inicio", {"intervals": [[3, 1]]}, invalid=True),
        ),
    ),
    KataDefinition(
        "kata-02",
        "Primeiro caractere unico",
        (
            AcceptanceCase("caso_normal", {"text": "swiss"}, 1),
            AcceptanceCase("unico_no_inicio", {"text": "aabbcd"}, 4),
            AcceptanceCase("sem_unico", {"text": "aabb"}, -1),
            AcceptanceCase("texto_vazio", {"text": ""}, -1),
            AcceptanceCase("tipo_invalido", {"text": 123}, invalid=True),
        ),
    ),
    KataDefinition(
        "kata-03",
        "Rotacao de matriz quadrada",
        (
            AcceptanceCase("uma_rotacao", {"grid": [[1, 2], [3, 4]], "turns": 1}, [[3, 1], [4, 2]]),
            AcceptanceCase("duas_rotacoes", {"grid": [[1, 2], [3, 4]], "turns": 2}, [[4, 3], [2, 1]]),
            AcceptanceCase("quatro_rotacoes", {"grid": [[7]], "turns": 4}, [[7]]),
            AcceptanceCase("turns_negativo_normalizado", {"grid": [[1, 2, 3], [4, 5, 6], [7, 8, 9]], "turns": -1}, [[3, 6, 9], [2, 5, 8], [1, 4, 7]]),
            AcceptanceCase("matriz_nao_quadrada", {"grid": [[1, 2], [3]], "turns": 1}, invalid=True),
        ),
    ),
    KataDefinition(
        "kata-04",
        "Troco com menor quantidade de moedas",
        (
            AcceptanceCase("caso_normal", {"amount": 6, "coins": [1, 3, 4]}, [0, 2, 0]),
            AcceptanceCase("moeda_exata", {"amount": 14, "coins": [1, 5, 10]}, [4, 0, 1]),
            AcceptanceCase("valor_zero", {"amount": 0, "coins": [1, 2]}, [0, 0]),
            AcceptanceCase("ordem_das_moedas", {"amount": 7, "coins": [5, 1, 2]}, [1, 0, 1]),
            AcceptanceCase("sem_combinacao", {"amount": 3, "coins": [2]}, invalid=True),
        ),
    ),
    KataDefinition(
        "kata-05",
        "Janela livre em agenda",
        (
            AcceptanceCase("primeira_janela", {"busy": [[60, 120], [180, 240]], "window": [0, 300], "duration": 30}, [0, 30]),
            AcceptanceCase("pula_conflito", {"busy": [[0, 45], [60, 90]], "window": [0, 120], "duration": 15}, [45, 60]),
            AcceptanceCase("limite_exato", {"busy": [], "window": [10, 40], "duration": 30}, [10, 40]),
            AcceptanceCase("agenda_desordenada", {"busy": [[50, 70], [10, 20]], "window": [0, 100], "duration": 20}, [20, 40]),
            AcceptanceCase("duracao_invalida", {"busy": [], "window": [0, 10], "duration": 0}, invalid=True),
        ),
    ),
    KataDefinition(
        "kata-06",
        "Contagem de picos",
        (
            AcceptanceCase("picos_separados", {"values": [1, 3, 1, 4, 2]}, 2),
            AcceptanceCase("platô_conta_um", {"values": [1, 3, 3, 1]}, 1),
            AcceptanceCase("pico_na_borda_nao_conta", {"values": [5, 1, 5]}, 0),
            AcceptanceCase("sequencia_curta", {"values": [2, 1]}, 0),
            AcceptanceCase("valores_nao_numericos", {"values": [1, "2", 1]}, invalid=True),
        ),
    ),
)


KATAS_BY_ID = {kata.kata_id: kata for kata in KATAS}

if len(KATAS) != 6:
    raise RuntimeError("o catalogo deve conter exatamente seis katas")
