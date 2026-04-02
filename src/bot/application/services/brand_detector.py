"""Auto-detect parts catalog brand from filename and content."""

from __future__ import annotations

import re

# Major automotive parts brands
KNOWN_BRANDS = {
    "bosch": ["bosch", "bosh"],
    "ngk": ["ngk", "n.g.k"],
    "champion": ["champion"],
    "denso": ["denso"],
    "beru": ["beru"],
    "mopar": ["mopar", "chrysler"],
    "delphi": ["delphi"],
    "valeo": ["valeo"],
    "magneti marelli": ["magneti", "marelli"],
    "delco": ["delco"],
    "acdelco": ["acdelco"],
    "acdel co": ["acdel"],
    "motorcraft": ["motorcraft"],
    "fram": ["fram"],
    "ac": ["ac filters", "ac automotive"],
    "sachs": ["sachs"],
    "bilstein": ["bilstein"],
    "kw": ["kw coilovers", "kw automotive"],
    "continental": ["continental", "conti"],
    "michelin": ["michelin"],
    "pirelli": ["pirelli"],
    "bridgestone": ["bridgestone"],
    "goodyear": ["goodyear"],
    "dunlop": ["dunlop"],
    "yokohama": ["yokohama"],
    "hella": ["hella"],
    "stanley": ["stanley"],
    "philips": ["philips"],
    "sylvania": ["sylvania"],
    "osram": ["osram"],
    "leoni": ["leoni"],
    "yazaki": ["yazaki"],
    "sumitomo": ["sumitomo"],
    "amphenol": ["amphenol"],
    "JAE": ["jae"],
    "TE Connectivity": ["te connectivity", "te connect"],
}

# Common keywords that indicate parts catalogs
CATALOG_KEYWORDS = ["catalog", "catálogo", "catalogue", "parts", "peças", "velas", "cabos", "ignição"]


def detect_brand_from_filename(filename: str) -> str | None:
    """Detect brand from filename.

    Args:
        filename: Original PDF filename (e.g., "Catalogo_Bosch_2024.pdf", "CatalogoNGK.pdf")

    Returns:
        Brand name (normalized) or None if not detected
    """
    if not filename:
        return None

    filename_lower = filename.lower()

    # Try exact matches with flexible separators
    for brand, keywords in KNOWN_BRANDS.items():
        for keyword in keywords:
            # Match with:
            # - word boundaries (\b)
            # - underscores, hyphens, spaces before/after
            # - OR at word boundary within CamelCase (e.g., CatalogoNGK)
            patterns = [
                r'(?:^|[\s_\-])' + re.escape(keyword) + r'(?:[\s_\-\.pdf]|$)',  # separated
                r'(?:^|[a-z])' + re.escape(keyword) + r'(?:[A-Z\d_\-\.]|$)',  # CamelCase (e.g., ...NGK_)
            ]
            for pattern in patterns:
                if re.search(pattern, filename_lower, re.IGNORECASE):
                    return brand.upper()

    return None


def detect_brand_from_content(content: str, max_chars: int = 5000) -> str | None:
    """Detect brand from PDF text content (first N chars).

    Look for brand mentions in headers, titles, or early content.

    Args:
        content: Extracted PDF text content
        max_chars: How much content to scan (first N chars)

    Returns:
        Brand name (normalized) or None if not detected
    """
    if not content:
        return None

    # Scan only first portion for performance
    scan_text = content[:max_chars].lower()

    # Weight early mentions higher by checking in sections
    sections = [
        scan_text[:500],   # Title/header section (100% weight)
        scan_text[500:2000],  # Content introduction (75% weight)
        scan_text[2000:max_chars],  # Rest (50% weight)
    ]

    for i, section in enumerate(sections):
        for brand, keywords in KNOWN_BRANDS.items():
            for keyword in keywords:
                # Look for brand name as word
                if re.search(r'\b' + re.escape(keyword) + r'\b', section):
                    return brand.upper()

    return None


def extract_brand(
    filename: str,
    content: str | None = None,
) -> str | None:
    """Extract brand from filename and optionally PDF content.

    Tries filename first (faster, usually has brand in name),
    then falls back to content if needed.

    Args:
        filename: Original PDF filename
        content: Extracted PDF text (optional, for fallback)

    Returns:
        Brand name (uppercase) or None if not detected
    """
    # Try filename first (most reliable)
    brand = detect_brand_from_filename(filename)
    if brand:
        return brand

    # Fall back to content analysis
    if content:
        brand = detect_brand_from_content(content)
        if brand:
            return brand

    return None
