from pathlib import Path


def get_project_root() -> Path:
    """Path to the root directory of the project."""
    return get_src_root().parent


def get_src_root() -> Path:
    """Path to the root directory of the source code for the project."""
    return Path(__file__).parent.parent.parent
