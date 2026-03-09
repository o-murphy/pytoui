import re
from functools import lru_cache
from pathlib import Path

FONT_WEIGHTS = {
    "thin": "Thin",
    "light": "Light",
    "regular": "Regular",
    "medium": "Medium",
    "semibold": "SemiBold",
    "bold": "Bold",
    "extrabold": "ExtraBold",
    "black": "Black",
}


# ---------------- Font discovery ----------------
@lru_cache(maxsize=1)
def get_fonts() -> dict[str, Path]:
    try:
        import pytoui

        root = Path(pytoui.__file__).parent
    except ImportError:
        root = Path(__file__).parent.parent

    candidates = [
        root / "assets" / "fonts",
        root / ".." / ".." / "assets" / "fonts",
    ]
    mapping: dict[str, Path] = {}

    for base in candidates:
        if not base.exists():
            continue
        for path in base.rglob("*.ttf"):
            mapping.setdefault(path.name, path.resolve())

    return mapping


# ---------------- Normalization ----------------
_PREFIX_RE = re.compile(r"^\.(SFUI|SFNS|SFPS|SFPro)-", re.IGNORECASE)
_SYSTEM_RE = re.compile(r"^<system(?:-(bold|italic))?>$", re.IGNORECASE)


def normalize_name(name: str) -> str:
    name_clean = name.strip()

    detected_weight = "Regular"

    lowered_name = name_clean.lower()
    for key, value in FONT_WEIGHTS.items():
        if key in lowered_name:
            detected_weight = value

    if "heavy" in lowered_name:
        detected_weight = "ExtraBold"

    m = _SYSTEM_RE.match(name_clean)
    if m:
        groups = [g for g in m.groups() if g]
        if groups:
            return groups[-1].capitalize()
        return "Regular"

    name_no_prefix = _PREFIX_RE.sub("", name_clean).replace("-", "")

    if "Semibold" in name_no_prefix:
        return "SemiBold"

    return detected_weight


# ---------------- Resolver ----------------
def resolve_font(family: str, internal_name: str, size: int = 16) -> Path | None:
    fonts = get_fonts()
    weight = normalize_name(internal_name)
    family_lower = family.lower()

    if family_lower == "inter":
        opt = "28pt" if size >= 20 else "18pt"
        filename = f"Inter_{opt}-{weight}.ttf"
        fallback = f"Inter_{opt}-Regular.ttf"
    elif family_lower == "roboto":
        filename = f"Roboto-{weight}.ttf"
        fallback = "Roboto-Regular.ttf"
    else:
        filename = f"{family}-{weight}.ttf"
        fallback = f"{family}-Regular.ttf"

    path = fonts.get(filename)
    if path and path.exists():
        return path
    fallback_path = fonts.get(fallback)
    if fallback_path and fallback_path.exists():
        return fallback_path
    return None


# ---------------- Universal resolver ----------------
def resolve_any_font(font: str, size: int = 16) -> Path | None:
    font = font.strip()

    known_families = ["Inter", "Roboto"]
    family = None
    for f in known_families:
        if f.lower() in font.lower():
            family = f
            break
    if family is None:
        family = "Inter"
    return resolve_font(family, font, size)


# ---------------- Test ----------------
def main():
    tests = [
        ".SFUI-Bold",
        ".SFUI-Regular",
        ".SFUI-BoldItalic",
        "Roboto-Medium",
        "<system>",
        "<system-bold>",
        "Inter-ExtraBold",
        "SomeUnknownFont-Bold",
    ]

    for t in tests:
        path = resolve_any_font(t, size=16)
        print(f"{t} -> {path}")


if __name__ == "__main__":
    main()
