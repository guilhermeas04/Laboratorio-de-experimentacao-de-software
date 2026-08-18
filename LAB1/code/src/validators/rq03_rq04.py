"""Validacao das metricas de RQ03 e RQ04 nos 1000 repositorios."""

from statistics import median, quantiles


def _as_int(value):
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _iqr_bounds(values: list[int]) -> tuple[float, float] | None:
    if len(values) < 4:
        return None

    ordered = sorted(values)
    q1, _, q3 = quantiles(ordered, n=4, method="inclusive")
    iqr = q3 - q1
    return q1 - 1.5 * iqr, q3 + 1.5 * iqr


def validate_sample(repositories: list[dict], sample_size: int = 10) -> None:
    """Mantem a checagem rapida usada na coleta."""
    summary = validate_dataset(repositories[:sample_size], expected_count=None)
    if summary["invalid"]:
        first = summary["invalid"][0]
        raise ValueError(f"{first['name']}: {first['reason']}")

    print(f"Validacao RQ03/RQ04 concluida para {summary['analyzed']} repositorios.")


def validate_dataset(
    repositories: list[dict],
    expected_count: int | None = 1000,
) -> dict:
    """Valida releases e atualizacao em todos os registros coletados."""
    if not repositories:
        raise ValueError("Nenhum repositorio recebido para validacao.")

    if expected_count is not None and len(repositories) != expected_count:
        raise ValueError(
            f"Esperados {expected_count} repositorios, recebidos {len(repositories)}."
        )

    missing: list[dict] = []
    invalid: list[dict] = []
    releases: list[int] = []
    days_update: list[int] = []
    days_push: list[int] = []

    for index, repository in enumerate(repositories, start=1):
        name = (repository.get("name_with_owner") or "").strip()
        if not name:
            invalid.append({"name": f"linha {index}", "reason": "sem name_with_owner"})
            continue

        updated_at = repository.get("updated_at")
        pushed_at = repository.get("pushed_at")
        days_since_last_update = _as_int(repository.get("days_since_last_update"))
        days_since_last_push = _as_int(repository.get("days_since_last_push"))
        releases_count = _as_int(repository.get("releases_count"))

        if not updated_at:
            missing.append({"name": name, "field": "updated_at"})
        if days_since_last_update is None:
            missing.append({"name": name, "field": "days_since_last_update"})
        elif days_since_last_update < 0:
            invalid.append(
                {
                    "name": name,
                    "reason": f"days_since_last_update invalido: {days_since_last_update}",
                }
            )
        else:
            days_update.append(days_since_last_update)

        if not pushed_at:
            missing.append({"name": name, "field": "pushed_at"})
        if days_since_last_push is None:
            missing.append({"name": name, "field": "days_since_last_push"})
        elif days_since_last_push < 0:
            invalid.append(
                {
                    "name": name,
                    "reason": f"days_since_last_push invalido: {days_since_last_push}",
                }
            )
        else:
            days_push.append(days_since_last_push)

        if releases_count is None:
            missing.append({"name": name, "field": "releases_count"})
        elif releases_count < 0:
            invalid.append(
                {"name": name, "reason": f"releases_count invalido: {releases_count}"}
            )
        else:
            releases.append(releases_count)

    release_bounds = _iqr_bounds(releases)
    update_bounds = _iqr_bounds(days_update)
    push_bounds = _iqr_bounds(days_push)

    release_outliers = []
    update_outliers = []
    push_outliers = []

    for repository in repositories:
        name = repository.get("name_with_owner")
        releases_count = _as_int(repository.get("releases_count"))
        days_since_last_update = _as_int(repository.get("days_since_last_update"))
        days_since_last_push = _as_int(repository.get("days_since_last_push"))

        if release_bounds and releases_count is not None:
            low, high = release_bounds
            if releases_count < low or releases_count > high:
                release_outliers.append((name, releases_count))

        if update_bounds and days_since_last_update is not None:
            low, high = update_bounds
            if days_since_last_update < low or days_since_last_update > high:
                update_outliers.append((name, days_since_last_update))

        if push_bounds and days_since_last_push is not None:
            low, high = push_bounds
            if days_since_last_push < low or days_since_last_push > high:
                push_outliers.append((name, days_since_last_push))

    return {
        "analyzed": len(repositories),
        "missing": missing,
        "invalid": invalid,
        "releases": releases,
        "days_update": days_update,
        "days_push": days_push,
        "release_outliers": sorted(release_outliers, key=lambda item: item[1], reverse=True),
        "update_outliers": sorted(update_outliers, key=lambda item: item[1], reverse=True),
        "push_outliers": sorted(push_outliers, key=lambda item: item[1], reverse=True),
        "updated_at_zero": sum(1 for value in days_update if value == 0),
        "pushed_at_zero": sum(1 for value in days_push if value == 0),
        "median_update": median(days_update) if days_update else None,
        "median_push": median(days_push) if days_push else None,
    }
