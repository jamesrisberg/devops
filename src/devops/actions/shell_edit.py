"""Shell config editing functions with backup support."""

import os
import shutil
from datetime import datetime
from pathlib import Path


def _get_backup_dir() -> Path:
    """Get or create the backup directory."""
    backup_dir = Path.home() / ".config" / "devops" / "backups"
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def backup_file(file_path: str) -> str:
    """Create a timestamped backup of a file.

    Args:
        file_path: Path to the file to backup

    Returns:
        Path to the backup file
    """
    backup_dir = _get_backup_dir()
    filename = os.path.basename(file_path)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{filename}.{timestamp}.bak"

    shutil.copy2(file_path, backup_path)
    return str(backup_path)


def update_alias(
    file_path: str,
    old_name: str,
    new_name: str,
    new_value: str,
    line_number: int,
) -> None:
    """Update an existing alias in a shell config file.

    Args:
        file_path: Path to the shell config file
        old_name: Current name of the alias
        new_name: New name for the alias
        new_value: New command value for the alias
        line_number: Line number where the alias is defined
    """
    backup_file(file_path)

    with open(file_path, "r") as f:
        lines = f.readlines()

    # Line numbers are 1-indexed
    idx = line_number - 1
    if 0 <= idx < len(lines):
        # Create new alias line
        new_line = f"alias {new_name}='{new_value}'\n"
        lines[idx] = new_line

    with open(file_path, "w") as f:
        f.writelines(lines)


def add_alias(file_path: str, name: str, value: str) -> None:
    """Add a new alias to the end of a shell config file.

    Args:
        file_path: Path to the shell config file
        name: Name of the alias
        value: Command value for the alias
    """
    backup_file(file_path)

    # Ensure file ends with newline
    with open(file_path, "r") as f:
        content = f.read()

    if not content.endswith("\n"):
        content += "\n"

    # Add the new alias
    new_alias = f"alias {name}='{value}'\n"
    content += new_alias

    with open(file_path, "w") as f:
        f.write(content)


def delete_item(
    file_path: str,
    line_number: int,
    item_type: str,
    end_line: int = None,
) -> None:
    """Delete an item (alias or function) from a shell config file.

    Args:
        file_path: Path to the shell config file
        line_number: Starting line number of the item
        item_type: Type of item ("alias" or "function")
        end_line: Ending line number for multi-line items (functions)
    """
    backup_file(file_path)

    with open(file_path, "r") as f:
        lines = f.readlines()

    # Line numbers are 1-indexed
    start_idx = line_number - 1

    if item_type == "function" and end_line:
        end_idx = end_line
        # Remove lines from start to end (inclusive)
        del lines[start_idx:end_idx]
    else:
        # Remove single line
        if 0 <= start_idx < len(lines):
            del lines[start_idx]

    with open(file_path, "w") as f:
        f.writelines(lines)


def update_function(
    file_path: str,
    name: str,
    new_body: str,
    start_line: int,
    end_line: int,
) -> None:
    """Update an existing function in a shell config file.

    Args:
        file_path: Path to the shell config file
        name: Name of the function
        new_body: New body content for the function
        start_line: Starting line number of the function
        end_line: Ending line number of the function
    """
    backup_file(file_path)

    with open(file_path, "r") as f:
        lines = f.readlines()

    # Line numbers are 1-indexed
    start_idx = start_line - 1
    end_idx = end_line

    # Create new function definition
    # Check if body already has function wrapper
    if new_body.strip().startswith(f"{name}()") or new_body.strip().startswith(
        "function "
    ):
        new_function = new_body.strip() + "\n"
    else:
        # Wrap body in function syntax
        new_function = f"{name}() {{\n    {new_body}\n}}\n"

    # Replace old function with new
    del lines[start_idx:end_idx]
    lines.insert(start_idx, new_function)

    with open(file_path, "w") as f:
        f.writelines(lines)


def add_function(file_path: str, name: str, body: str) -> None:
    """Add a new function to the end of a shell config file.

    Args:
        file_path: Path to the shell config file
        name: Name of the function
        body: Body content for the function
    """
    backup_file(file_path)

    # Ensure file ends with newline
    with open(file_path, "r") as f:
        content = f.read()

    if not content.endswith("\n"):
        content += "\n"

    # Add the new function
    # Check if body already has function wrapper
    if body.strip().startswith(f"{name}()") or body.strip().startswith("function "):
        new_function = f"\n{body.strip()}\n"
    else:
        # Wrap body in function syntax
        new_function = f"\n{name}() {{\n    {body}\n}}\n"

    content += new_function

    with open(file_path, "w") as f:
        f.write(content)
