from lab04_hypothesis.collect_real_data import bot_group, duration_hours


def test_bot_group_uses_type_and_login_rules() -> None:
    assert bot_group({"user": {"type": "Bot", "login": "renovate"}}) == "bot"
    assert bot_group({"user": {"type": "User", "login": "dependabot[bot]"}}) == "bot"
    assert bot_group({"user": {"type": "User", "login": "amandabicalh"}}) == "human"


def test_duration_hours_uses_created_and_merged_timestamps() -> None:
    pull_request = {
        "created_at": "2026-01-01T10:00:00Z",
        "merged_at": "2026-01-02T10:30:00Z",
    }

    assert duration_hours(pull_request) == 24.5
    assert duration_hours({"created_at": "2026-01-01T10:00:00Z"}) is None
    assert duration_hours({"created_at": "2026-01-02T10:00:00Z", "merged_at": "2026-01-01T10:00:00Z"}) is None