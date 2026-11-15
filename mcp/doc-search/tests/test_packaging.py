"""Verify the checkout launcher still resolves the same workspace."""
import os
from pathlib import Path
import subprocess
import sys


SERVER_DIR = Path(__file__).resolve().parents[1]


def test_checkout_workspace_root_without_environment():
    env = os.environ.copy()
    env.pop("AI_WORKSPACE_ROOT", None)
    result = subprocess.run(
        [sys.executable, "-c", "from doc_search.server import ROOT; print(ROOT)"],
        cwd=SERVER_DIR, env=env, capture_output=True, text=True, check=True,
    )
    assert Path(result.stdout.strip()) == SERVER_DIR.parents[1]
