#!/usr/bin/env python3
"""Instructions for obtaining Warcraft Peon sound files.

The peon voice lines are copyrighted by Blizzard Entertainment and are not
included in this repository. You need to download them yourself for personal use.

Usage:
    python scripts/download_peon_sounds.py
"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOUNDS_DIR = PROJECT_ROOT / "sounds"

REQUIRED_FILES = {
    "ready-to-work.mp3": '"Ready to work!" — startup acknowledgment',
    "work-work.mp3": '"Work, work." — task acceptance',
    "yes.mp3": '"Yes?" — selection response',
    "i-can-do-that.mp3": '"I can do that." — task acceptance',
    "be-happy-to.mp3": '"Be happy to." — task acceptance',
    "hmm.mp3": '"Hmm?" — selection response',
    "something-you-re-doing.mp3": '"Something you\'re doing?" — annoyed/confused',
}

SOURCES = [
    "https://www.101soundboards.com/boards/10028-warcraft-ii-peon",
    "https://wowpedia.fandom.com/wiki/Peon_(Warcraft_II)",
]


def main():
    SOUNDS_DIR.mkdir(parents=True, exist_ok=True)

    existing = [f for f in REQUIRED_FILES if (SOUNDS_DIR / f).exists()]
    missing = [f for f in REQUIRED_FILES if not (SOUNDS_DIR / f).exists()]

    if not missing:
        print("All peon sounds are already in place!\n")
        print("Next steps:")
        print("  python scripts/map_peon_sounds.py")
        print("  python -m peon_dreame build --input-dir sounds/mapped/")
        return

    print("Warcraft Peon sound files needed")
    print("=" * 40)
    print()
    print("The peon voice lines are copyrighted by Blizzard Entertainment")
    print("and are not included in this repository. Download them yourself")
    print("for personal use from one of these sources:")
    print()
    for url in SOURCES:
        print(f"  {url}")
    print()
    print(f"Save the following files to: {SOUNDS_DIR}/")
    print()

    for filename, desc in REQUIRED_FILES.items():
        status = "OK" if filename in existing else "MISSING"
        marker = "  " if filename in existing else ">>"
        print(f"  {marker} {filename:<35} {desc:<45} [{status}]")

    print()
    if existing:
        print(f"{len(existing)}/{len(REQUIRED_FILES)} files present, {len(missing)} still needed.")
    else:
        print(f"0/{len(REQUIRED_FILES)} files present. Download all {len(missing)} files above.")

    print()
    print("Once all files are in place, run:")
    print("  python scripts/map_peon_sounds.py")
    print("  python -m peon_dreame build --input-dir sounds/mapped/")


if __name__ == "__main__":
    main()
