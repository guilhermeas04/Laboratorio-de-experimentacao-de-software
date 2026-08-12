"""Validacao rapida das metricas de RQ01 e RQ02."""


def validate_sample(repositories: list[dict], sample_size: int = 10) -> None:
    """Valida idade do repositorio e pull requests aceitas em uma amostra."""
    if not repositories:
        raise ValueError("Nenhum repositorio recebido para validacao.")

    sample = repositories[:sample_size]

    for index, repository in enumerate(sample, start=1):
        name = repository.get("name_with_owner")
        created_at = repository.get("created_at")
        age_days = repository.get("repository_age_days")
        merged_prs = repository.get("merged_pull_requests")

        if not name:
            raise ValueError(f"Amostra {index}: repositorio sem name_with_owner.")
        if not created_at:
            raise ValueError(f"{name}: created_at ausente.")
        if not isinstance(age_days, int) or age_days < 0:
            raise ValueError(f"{name}: idade invalida em dias: {age_days}.")
        if not isinstance(merged_prs, int) or merged_prs < 0:
            raise ValueError(f"{name}: total de PRs aceitas invalido: {merged_prs}.")

    print(f"Validacao RQ01/RQ02 concluida para {len(sample)} repositorios.")
