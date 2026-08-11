"""Configuracoes da coleta do Lab01."""

from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


@dataclass(frozen=True)
class Settings:
    github_token: str
    github_graphql_url: str
    top_repositories_limit: int


def load_settings() -> Settings:
    """Carrega configuracoes a partir de variaveis de ambiente."""
    load_dotenv(ENV_PATH)

    return Settings(
        github_token=os.getenv("GITHUB_TOKEN", ""),
        github_graphql_url=os.getenv(
            "GITHUB_GRAPHQL_URL",
            "https://api.github.com/graphql",
        ),
        top_repositories_limit=int(os.getenv("GITHUB_TOP_REPOSITORIES_LIMIT", "100")),
    )
