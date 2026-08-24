"""Pipeline compartilhado de carga, validacao e visualizacao."""

from visualization.figures import FIGURES_DIR, figure_path
from visualization.loader import load_top_repositories
from visualization.style import apply_common_style, save_figure

__all__ = [
    "FIGURES_DIR",
    "apply_common_style",
    "figure_path",
    "load_top_repositories",
    "save_figure",
]
