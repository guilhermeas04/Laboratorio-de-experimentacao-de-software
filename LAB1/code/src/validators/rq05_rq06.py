"""Validacao das metricas de RQ05 e RQ06 nos repositorios coletados."""

from math import isclose


POPULAR_LANGUAGES_SOURCE = (
    "GitHub Octoverse 2024 - "
    "https://github.blog/news-insights/octoverse/octoverse-2024/"
)
POPULAR_LANGUAGES = frozenset(
    {"Python", "JavaScript", "TypeScript", "Java", "C#", "C++", "PHP", "Shell", "C", "Go"}
)


def validate_sample(repositories: list[dict], sample_size: int = 10) -> None:
    """Valida linguagem primaria e issues fechadas em uma amostra."""
    summary = validate_dataset(repositories[:sample_size], expected_count=None)
    print(f"Validacao RQ05/RQ06 concluida para {summary['analyzed']} repositorios.")


def validate_dataset(
    repositories: list[dict], expected_count: int | None = 1000
) -> dict:
    """Valida RQ05/RQ06 e retorna os recortes usados pelas metricas."""
    if not repositories:
        raise ValueError("Nenhum repositorio recebido para validacao.")
    if expected_count is not None and len(repositories) != expected_count:
        raise ValueError(
            f"Esperados {expected_count} repositorios, recebidos {len(repositories)}."
        )

    languages: dict[str, int] = {}
    popular_language_count = 0
    ratios: list[float] = []

    for index, repository in enumerate(repositories, start=1):
        name = repository.get("name_with_owner") or f"linha {index}"
        primary_language = repository.get("primary_language")
        if not isinstance(primary_language, str):
            raise ValueError(f"{name}: linguagem primaria invalida: {primary_language}.")
        language = primary_language.strip()
        languages[language] = languages.get(language, 0) + 1
        if language in POPULAR_LANGUAGES:
            popular_language_count += 1

        total_issues = repository.get("total_issues")
        closed_issues = repository.get("closed_issues")
        ratio = repository.get("closed_issues_ratio")
        if not isinstance(total_issues, int) or isinstance(total_issues, bool) or total_issues < 0:
            raise ValueError(f"{name}: total de issues invalido: {total_issues}.")
        if not isinstance(closed_issues, int) or isinstance(closed_issues, bool) or closed_issues < 0:
            raise ValueError(f"{name}: total de issues fechadas invalido: {closed_issues}.")
        if closed_issues > total_issues:
            raise ValueError(f"{name}: issues fechadas maiores que o total de issues.")
        if total_issues == 0:
            if ratio is not None:
                raise ValueError(f"{name}: razao deve ser None quando total_issues = 0.")
            continue
        if not isinstance(ratio, (int, float)) or isinstance(ratio, bool):
            raise ValueError(f"{name}: razao de issues fechadas invalida: {ratio}.")
        expected_ratio = closed_issues / total_issues
        if not 0.0 <= ratio <= 1.0 or not isclose(ratio, expected_ratio, rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"{name}: razao inconsistente com closed/total.")
        ratios.append(float(ratio))

    return {
        "analyzed": len(repositories),
        "languages": languages,
        "popular_language_count": popular_language_count,
        "ratios": ratios,
        "popular_languages_source": POPULAR_LANGUAGES_SOURCE,
    }
