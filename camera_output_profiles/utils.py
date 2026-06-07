"""Pure helpers shared by the Blender-facing add-on modules."""

from __future__ import annotations

from datetime import datetime
from math import gcd
import os
from pathlib import Path
import re
from string import Formatter
from typing import Any, Callable, Mapping


ALLOWED_TEMPLATE_TOKENS = frozenset(
    {"camera", "width", "height", "frame", "format", "date", "scene"}
)

FILE_EXTENSIONS = {
    "PNG": ".png",
    "JPEG": ".jpg",
    "WEBP": ".webp",
}

_INVALID_FILENAME_CHARACTERS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WHITESPACE = re.compile(r"\s+")
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


class TemplateError(ValueError):
    """Raised when a filename template cannot be safely expanded."""


def sanitize_filename(value: str, fallback: str = "camera_output") -> str:
    """Return a single safe filename component without an extension."""
    cleaned = _WHITESPACE.sub(" ", value.strip())
    cleaned = _INVALID_FILENAME_CHARACTERS.sub("_", cleaned)
    cleaned = cleaned.strip(" .")
    return cleaned or fallback


def sanitize_subfolder(value: str) -> Path:
    """Return a relative folder path with traversal segments removed."""
    parts: list[str] = []
    for raw_part in value.replace("\\", "/").split("/"):
        part = raw_part.strip()
        if not part or part in {".", ".."}:
            continue
        safe_part = sanitize_filename(part, fallback="")
        if safe_part:
            parts.append(safe_part)
    return Path(*parts) if parts else Path()


def validate_output_subfolder(value: str) -> Path:
    """Validate a relative output subfolder and return its sanitized path."""
    normalized = value.strip().replace("\\", "/")
    if not normalized:
        return Path()
    if normalized.startswith("/") or _WINDOWS_DRIVE.match(normalized):
        raise ValueError("Output subfolder must be relative to the Base Output Folder.")

    parts = normalized.split("/")
    if any(part == ".." for part in parts):
        raise ValueError("Output subfolder cannot contain path traversal ('..').")
    return sanitize_subfolder(value)


def extract_template_tokens(template: str) -> set[str]:
    """Parse and validate template fields."""
    if not template.strip():
        raise TemplateError("Filename template is empty.")
    if "/" in template or "\\" in template or ".." in template:
        raise TemplateError(
            "Filename template cannot contain path separators or path traversal."
        )

    tokens: set[str] = set()
    try:
        parsed = Formatter().parse(template)
        for _, field_name, _, _ in parsed:
            if field_name is None:
                continue
            if field_name not in ALLOWED_TEMPLATE_TOKENS:
                raise TemplateError(f"Unsupported filename token: {{{field_name}}}")
            tokens.add(field_name)
    except ValueError as exc:
        raise TemplateError(f"Invalid filename template: {exc}") from exc
    return tokens


def render_filename_template(
    template: str,
    values: Mapping[str, Any],
) -> str:
    """Expand a validated template and sanitize it as one filename."""
    extract_template_tokens(template)
    try:
        rendered = template.format_map(dict(values))
    except (KeyError, ValueError, TypeError) as exc:
        raise TemplateError(f"Could not format filename template: {exc}") from exc
    return sanitize_filename(rendered)


def extension_for_format(file_format: str) -> str:
    try:
        return FILE_EXTENSIONS[file_format]
    except KeyError as exc:
        raise ValueError(f"Unsupported file format: {file_format}") from exc


def build_template_values(
    *,
    camera_name: str,
    scene_name: str,
    width: int,
    height: int,
    frame: int,
    file_format: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    timestamp = now or datetime.now()
    return {
        "camera": camera_name,
        "width": width,
        "height": height,
        "frame": frame,
        "format": file_format.lower(),
        "date": timestamp.strftime("%Y-%m-%d"),
        "scene": scene_name,
    }


def build_output_path(
    base_path: Path,
    output_subfolder: str,
    filename_template: str,
    template_values: Mapping[str, Any],
    file_format: str,
) -> Path:
    filename = render_filename_template(filename_template, template_values)
    extension = extension_for_format(file_format)
    subfolder = validate_output_subfolder(output_subfolder)
    return base_path / subfolder / f"{filename}{extension}"


def resolve_output_base(
    render_filepath: str,
    abspath: Callable[[str], str],
) -> Path:
    """Resolve Blender's configured output path as the add-on base folder."""
    if not render_filepath.strip():
        raise ValueError("Scene output path is empty.")
    resolved = abspath(render_filepath)
    if not resolved.strip():
        raise ValueError("Scene output path could not be resolved.")
    base_path = Path(os.path.abspath(os.path.expanduser(resolved)))
    if base_path.exists() and not base_path.is_dir():
        raise ValueError("Base Output Folder points to a file, not a folder.")
    return base_path


def aspect_ratio_label(width: int, height: int) -> str:
    if width <= 0 or height <= 0:
        return "Invalid"
    divisor = gcd(width, height)
    ratio = (width // divisor, height // divisor)
    common = {
        (16, 9): "16:9",
        (1, 1): "1:1",
        (4, 5): "4:5",
        (9, 16): "9:16",
    }
    return common.get(ratio, "Custom")


def compact_path(path: Path, max_length: int = 54) -> str:
    text = str(path)
    if len(text) <= max_length:
        return text
    return f"...{text[-(max_length - 3):]}"
