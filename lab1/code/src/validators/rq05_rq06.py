"""Validacao rapida das metricas de RQ05 e RQ06."""


def validate_sample(repositories: list[dict], sample_size: int = 10) -> None:
    """Valida linguagem primaria e percentual de issues fechadas em uma amostra."""
    if not repositories:
        raise ValueError("Nenhum repositorio recebido para validacao.")

    sample = repositories[:sample_size]

    for index, repository in enumerate(sample, start=1):
        name = repository.get("name_with_owner")
        primary_language = repository.get("primary_language")
        total_issues = repository.get("total_issues")
        closed_issues = repository.get("closed_issues")
        closed_issues_ratio = repository.get("closed_issues_ratio")

        if not name:
            raise ValueError(f"Amostra {index}: repositorio sem name_with_owner.")

        if not isinstance(primary_language, str):
            raise ValueError(
                f"{name}: linguagem primaria invalida: {primary_language}."
            )

        if not isinstance(total_issues, int) or total_issues < 0:
            raise ValueError(f"{name}: total de issues invalido: {total_issues}.")

        if not isinstance(closed_issues, int) or closed_issues < 0:
            raise ValueError(f"{name}: total de issues fechadas invalido: {closed_issues}.")

        if closed_issues > total_issues:
            raise ValueError(
                f"{name}: issues fechadas ({closed_issues}) maior que o total "
                f"({total_issues})."
            )

        if total_issues == 0:
            if closed_issues_ratio is not None:
                raise ValueError(
                    f"{name}: razao de issues fechadas deve ser None quando "
                    "total_issues = 0."
                )
            continue

        if not isinstance(closed_issues_ratio, float):
            raise ValueError(
                f"{name}: razao de issues fechadas invalida: {closed_issues_ratio}."
            )

        if not 0.0 <= closed_issues_ratio <= 1.0:
            raise ValueError(
                f"{name}: razao de issues fechadas fora de [0, 1]: "
                f"{closed_issues_ratio}."
            )

        expected_ratio = closed_issues / total_issues
        if abs(closed_issues_ratio - expected_ratio) > 1e-9:
            raise ValueError(
                f"{name}: razao inconsistente com closed/total "
                f"({closed_issues_ratio} != {expected_ratio})."
            )

    print(f"Validacao RQ05/RQ06 concluida para {len(sample)} repositorios.")
