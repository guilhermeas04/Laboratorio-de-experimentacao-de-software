"""Validacao das metricas de RQ01 e RQ02."""

from datetime import datetime


def validate_sample(repositories: list[dict], sample_size: int = 10) -> None:
    """Valida idade do repositorio e pull requests aceitas em uma amostra."""
    summary = validate_dataset(repositories[:sample_size], expected_count=None)
    print(f"Validacao RQ01/RQ02 concluida para {summary['analyzed']} repositorios.")


def validate_dataset(
    repositories: list[dict], expected_count: int | None = 1000
) -> dict:
    """Valida todos os registros e retorna contagens de integridade."""
    if not repositories:
        raise ValueError("Nenhum repositorio recebido para validacao.")
    if expected_count is not None and len(repositories) != expected_count:
        raise ValueError(
            f"Esperados {expected_count} repositorios, recebidos {len(repositories)}."
        )

    names: set[str] = set()
    duplicate_names: list[str] = []
    missing = {
        "name_with_owner": 0,
        "created_at": 0,
        "repository_age_days": 0,
        "merged_pull_requests": 0,
    }

    for index, repository in enumerate(repositories, start=1):
        name = repository.get("name_with_owner")
        created_at = repository.get("created_at")
        age_days = repository.get("repository_age_days")
        merged_prs = repository.get("merged_pull_requests")

        if not name:
            missing["name_with_owner"] += 1
            name = f"linha {index}"
        elif name in names:
            duplicate_names.append(name)
        else:
            names.add(name)
        if not created_at:
            missing["created_at"] += 1
        else:
            try:
                datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            except (AttributeError, TypeError, ValueError) as error:
                raise ValueError(f"{name}: created_at invalido: {created_at}.") from error
        if age_days is None:
            missing["repository_age_days"] += 1
        elif not isinstance(age_days, int) or isinstance(age_days, bool) or age_days < 0:
            raise ValueError(f"{name}: idade invalida em dias: {age_days}.")
        if merged_prs is None:
            missing["merged_pull_requests"] += 1
        elif not isinstance(merged_prs, int) or isinstance(merged_prs, bool) or merged_prs < 0:
            raise ValueError(f"{name}: total de PRs aceitas invalido: {merged_prs}.")

    missing_total = sum(missing.values())
    if missing_total:
        raise ValueError(f"Foram encontrados {missing_total} campos ausentes: {missing}.")
    if duplicate_names:
        examples = ", ".join(duplicate_names[:5])
        raise ValueError(
            f"Foram encontrados {len(duplicate_names)} repositorios duplicados: {examples}."
        )

    return {
        "analyzed": len(repositories),
        "unique_repositories": len(names),
        "missing": missing,
        "duplicate_count": len(duplicate_names),
    }
