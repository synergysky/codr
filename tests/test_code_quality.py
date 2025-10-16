"""Code quality tests (linting, formatting, type checking)."""

import subprocess
from pathlib import Path


# Find venv executables
def _get_venv_executable(name: str) -> str:
    """Get path to executable in venv."""
    venv_path = Path(__file__).parent.parent / "venv" / "bin" / name
    if venv_path.exists():
        return str(venv_path)
    # Fallback to system executable
    return name


def test_ruff_check() -> None:
    """Test that code passes ruff linting."""
    result = subprocess.run(
        [_get_venv_executable("ruff"), "check", "app/", "tests/"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0, f"Ruff check failed:\n{result.stdout}\n{result.stderr}"


def test_mypy_check() -> None:
    """Test that code passes mypy type checking."""
    result = subprocess.run(
        [_get_venv_executable("mypy"), "app/"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0, f"Mypy check failed:\n{result.stdout}\n{result.stderr}"


def test_ruff_format_check() -> None:
    """Test that code is properly formatted (no changes needed)."""
    result = subprocess.run(
        [_get_venv_executable("ruff"), "format", "--check", "app/", "tests/"],
        capture_output=True,
        text=True,
        cwd=str(Path(__file__).parent.parent),
    )
    assert result.returncode == 0, f"Ruff format check failed:\n{result.stdout}\n{result.stderr}"
