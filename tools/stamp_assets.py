"""
Stamp CSS/JS links with a content hash so browsers pick up changes immediately.

GitHub Pages serves assets with `cache-control: max-age=600`. Without a cache
buster, a visitor who loaded the old script.js keeps it for ten minutes — which
is how /social/ ended up with no case studies: the stale script still used a
relative fetch path that 404s from a subdirectory.

Run this before pushing whenever assets/style.css or assets/script.js change.
"""

import hashlib
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ["index.html", "social/index.html"]
ASSETS = ["assets/style.css", "assets/script.js"]


def short_hash(path: pathlib.Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()[:8]


def main() -> None:
    versions = {a: short_hash(ROOT / a) for a in ASSETS}

    for page in PAGES:
        p = ROOT / page
        if not p.exists():
            print(f"  skip (missing): {page}")
            continue

        html = p.read_text()
        before = html

        for asset, ver in versions.items():
            # match /assets/style.css, optionally already carrying a ?v=...
            html = re.sub(
                rf'(["\'])/{re.escape(asset)}(?:\?v=[0-9a-f]+)?\1',
                rf'\g<1>/{asset}?v={ver}\g<1>',
                html,
            )

        if html != before:
            p.write_text(html)
            print(f"  stamped: {page}")
        else:
            print(f"  unchanged: {page}")

    for a, v in versions.items():
        print(f"    {a} -> v={v}")


if __name__ == "__main__":
    main()
