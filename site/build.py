"""Build the website. Thin wrapper so the build runs without installing the package.

    python site/build.py                  production build into site/dist/ (refuses placeholders)
    python site/build.py --draft          same pages, placeholders highlighted, noindex
    python site/build.py --preview FILE   the whole site as one HTML file for review
    python site/build.py --images         regenerate share images and icons (needs Pillow)

The code lives in ``src/leadgen/website/``; content in ``site/content/``;
layouts in ``site/templates/``.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from leadgen.website.build import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(root=ROOT))
