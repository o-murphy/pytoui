import re
from functools import lru_cache
from pathlib import Path


# ---------------- Font discovery ----------------
@lru_cache(maxsize=1)
def get_fonts() -> dict[str, Path]:
    try:
        import pytoui

        root = Path(pytoui.__file__).parent
    except ImportError:
        root = Path(__file__).parent

    candidates = [
        root / "ui" / "assets" / "fonts",
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
    name = name.strip()
    m = _SYSTEM_RE.match(name)
    if m:
        style = m.group(1)
        if not style:
            return "Regular"
        return style.capitalize()

    name = _PREFIX_RE.sub("", name)
    name = name.replace("-", "")
    if name.lower() == "heavy":
        return "ExtraBold"
    if "Semibold" in name:
        name = name.replace("Semibold", "SemiBold")
    return name


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
    """
    Універсальна функція:
    - будь-яка назва шрифту
    - SFUI/Apple-style
    - <system> / <system-bold> / <system-italic>
    - для невідомих сімейств дефолтно Inter
    """
    font = font.strip()

    # Визначаємо сімейство з назви, якщо можливо
    known_families = ["Inter", "Roboto"]
    family = None
    for f in known_families:
        if f.lower() in font.lower():
            family = f
            break
    if family is None:
        # Якщо невідома родина — дефолтно Inter
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
