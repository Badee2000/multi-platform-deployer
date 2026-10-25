"""Tests for the git-cleanliness helper used before every deploy."""

import pytest

from multi_platform_deployer.utils.helpers import has_uncommitted_changes


@pytest.mark.parametrize(
    "porcelain",
    [
        "",
        "\n",
        "?? .deployment/\n",
        "?? .deployment/render_1.json\n",
        " M .deployment/render_1.json\n",
        '?? ".deployment/with space.json"\n',
    ],
)
def test_state_dir_alone_is_not_a_change(porcelain):
    assert has_uncommitted_changes(porcelain) is False


@pytest.mark.parametrize(
    "porcelain",
    [
        " M app.py\n",
        "?? new_file.py\n",
        "?? .deployment/\n M app.py\n",
        "?? .deployment-backup/\n",
        "?? .deployment.yaml\n",
        "?? src/.deployment/x\n",
    ],
)
def test_real_changes_are_still_detected(porcelain):
    assert has_uncommitted_changes(porcelain) is True
