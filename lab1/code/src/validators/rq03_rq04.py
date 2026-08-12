"""Validacao rapida das metricas de RQ03 e RQ04."""


def validate_sample(repositories: list[dict], sample_size: int = 10) -> None:
    """Valida releases e tempo ate a ultima atualizacao em uma amostra."""
    if not repositories:
        raise ValueError("Nenhum repositorio recebido para validacao.")

    sample = repositories[:sample_size]

    for index, repository in enumerate(sample, start=1):
        name = repository.get("name_with_owner")
        updated_at = repository.get("updated_at")
        days_since_last_update = repository.get("days_since_last_update")
        releases_count = repository.get("releases_count")

        if not name:
            raise ValueError(f"Amostra {index}: repositorio sem name_with_owner.")
        if not updated_at:
            raise ValueError(f"{name}: updated_at ausente.")
        if not isinstance(days_since_last_update, int) or days_since_last_update < 0:
            raise ValueError(
                f"{name}: tempo ate a ultima atualizacao invalido: "
                f"{days_since_last_update}."
            )
        if not isinstance(releases_count, int) or releases_count < 0:
            raise ValueError(f"{name}: total de releases invalido: {releases_count}.")

    print(f"Validacao RQ03/RQ04 concluida para {len(sample)} repositorios.")
