import csv
from pathlib import Path

from lab03_dora.pipeline.select_repositories import main


def test_cli_generates_selection_and_funnel_from_input_csv(tmp_path: Path) -> None:
    input_csv = tmp_path / "candidates.csv"
    selection_out = tmp_path / "selection.csv"
    funnel_out = tmp_path / "funnel.csv"
    candidates_out = tmp_path / "unused_candidates.csv"
    config = tmp_path / "config.json"

    config.write_text(
        """
        {
          "selection": {
            "target_s01_sample_size": 1,
            "minimum_releases": 5,
            "minimum_valid_workflow_runs": 50
          }
        }
        """,
        encoding="utf-8",
    )
    with input_csv.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "full_name",
                "archived",
                "disabled",
                "has_actions",
                "releases_count",
                "valid_workflow_runs_count",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "full_name": "example/ok",
                "archived": "False",
                "disabled": "False",
                "has_actions": "True",
                "releases_count": "5",
                "valid_workflow_runs_count": "50",
            }
        )
        writer.writerow(
            {
                "full_name": "example/no-actions",
                "archived": "False",
                "disabled": "False",
                "has_actions": "False",
                "releases_count": "5",
                "valid_workflow_runs_count": "50",
            }
        )

    exit_code = main(
        [
            "--config",
            str(config),
            "--input-csv",
            str(input_csv),
            "--candidates-out",
            str(candidates_out),
            "--selection-out",
            str(selection_out),
            "--funnel-out",
            str(funnel_out),
        ]
    )

    assert exit_code == 0
    assert selection_out.is_file()
    assert funnel_out.is_file()
    assert not candidates_out.exists()

    rows = list(csv.DictReader(selection_out.open(encoding="utf-8")))
    assert rows[0]["selection_status"] == "eligible_s01"
    assert rows[1]["exclusion_reason"] == "no_github_actions"
