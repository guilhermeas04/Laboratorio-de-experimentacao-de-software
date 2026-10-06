"""Infraestrutura resiliente para acesso à API do GitHub."""

from .client import GitHubApiClient, RateLimitError, TemporaryApiError

__all__ = ["GitHubApiClient", "RateLimitError", "TemporaryApiError"]
