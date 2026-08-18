"""Validacao dos recortes de RQ07 por linguagem primaria."""


def group_by_language(repositories: list[dict]) -> dict[str, list[dict]]:
    """Agrupa as metricas de RQ02, RQ03 e RQ04 por linguagem."""
    groups: dict[str, list[dict]] = {}
    for repository in repositories:
        language = repository["primary_language"].strip()
        groups.setdefault(language, []).append(
            {
                "name_with_owner": repository["name_with_owner"],
                "merged_pull_requests": repository["merged_pull_requests"],
                "releases_count": repository["releases_count"],
                "days_since_last_update": repository["days_since_last_update"],
            }
        )
    return groups


def validate_dataset(
    repositories: list[dict], expected_count: int | None = 1000
) -> dict[str, list[dict]]:
    """Valida os campos que sustentam a comparacao da RQ07 por linguagem."""
    if not repositories:
        raise ValueError("Nenhum repositorio recebido para validacao.")
    if expected_count is not None and len(repositories) != expected_count:
        raise ValueError(
            f"Esperados {expected_count} repositorios, recebidos {len(repositories)}."
        )

    required = ("merged_pull_requests", "releases_count", "days_since_last_update")
    for index, repository in enumerate(repositories, start=1):
        name = repository.get("name_with_owner") or f"linha {index}"
        if not isinstance(repository.get("primary_language"), str):
            raise ValueError(f"{name}: linguagem primaria ausente ou invalida.")
        for field in required:
            value = repository.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(f"{name}: {field} invalido: {value}.")

    return group_by_language(repositories)


def validate_sample(repositories: list[dict], sample_size: int = 10) -> None:
    """Valida os campos de RQ07 em uma amostra da coleta."""
    groups = validate_dataset(repositories[:sample_size], expected_count=None)
    print(f"Validacao RQ07 concluida para {sum(len(items) for items in groups.values())} repositorios.")