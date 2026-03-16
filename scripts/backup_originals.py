#!/usr/bin/env python3
"""Download the original Dreame X50 Ultra voice files from the community repository.

Saves all stock .ogg files into a local backup directory so you can restore
them later by running:
    python -m peon_dreame build --input-dir originals/ --output stock_voice.tar.gz
    python -m peon_dreame install --pack stock_voice.tar.gz --ip <IP> --token <TOKEN>
"""

import csv
import ssl
import sys
import tarfile
import tempfile
import urllib.request
import urllib.error
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOUND_LIST_CSV = PROJECT_ROOT / "peon_dreame" / "sound_list.csv"
BACKUP_DIR = PROJECT_ROOT / "originals"

# Pre-packaged release with all original English voice files
RELEASE_URL = (
    "https://github.com/Makers-Im-Zigerschlitz/voicepacks_dreame/"
    "releases/download/0.1/original-en.tar.gz"
)

# Fallback: individual file downloads
INDIVIDUAL_BASE_URL = (
    "https://raw.githubusercontent.com/"
    "Makers-Im-Zigerschlitz/voicepacks_dreame/main/"
    "soundpacks/original-en/output"
)


def _make_ssl_context():
    """Create an SSL context, using certifi certs if available."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_ssl_ctx = _make_ssl_context()


def download(url):
    """Download a URL and return the bytes, or None on failure."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, context=_ssl_ctx) as resp:
            return resp.read()
    except (urllib.error.HTTPError, urllib.error.URLError) as e:
        return None


def download_release_tarball():
    """Download the pre-packaged tar.gz and extract .ogg files."""
    print(f"Downloading original-en.tar.gz from GitHub releases...")
    print(f"  {RELEASE_URL}\n")

    data = download(RELEASE_URL)
    if data is None:
        return False

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".tar.gz") as tmp:
        tmp.write(data)
        tmp.flush()

        with tarfile.open(tmp.name, "r:gz") as tar:
            count = 0
            for member in tar.getmembers():
                if not member.name.endswith(".ogg"):
                    continue
                # Extract just the filename (strip any directory prefix)
                basename = Path(member.name).name
                if not basename[0].isdigit():
                    continue
                member.name = basename
                tar.extract(member, BACKUP_DIR, filter="data")
                count += 1
                print(f"  {basename}")

    print(f"\nExtracted {count} files to {BACKUP_DIR}/")
    return count > 0


def download_individual_files():
    """Fallback: download files one by one."""
    ids = []
    with open(SOUND_LIST_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ids.append(int(row["id"]))

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {len(ids)} individual files as fallback...\n")

    succeeded = 0
    for sid in ids:
        filename = f"{sid}.ogg"
        dest = BACKUP_DIR / filename
        url = f"{INDIVIDUAL_BASE_URL}/{filename}"

        if dest.exists():
            print(f"  {filename} — already exists, skipping")
            succeeded += 1
            continue

        sys.stdout.write(f"  {filename} — downloading... ")
        sys.stdout.flush()
        data = download(url)
        if data:
            dest.write_bytes(data)
            print("ok")
            succeeded += 1
        else:
            print("not found")

    print(f"\n{succeeded}/{len(ids)} files downloaded to {BACKUP_DIR}/")
    return succeeded > 0


def main():
    if not download_release_tarball():
        print("Release download failed, trying individual files...\n")
        if not download_individual_files():
            print("Error: Could not download original voice files.", file=sys.stderr)
            print("You can restore the default voice via the Dreame app:", file=sys.stderr)
            print("  Settings → Voice Pack → select the default/standard voice", file=sys.stderr)
            sys.exit(1)

    print(f"\nTo restore stock sounds on your robot:")
    print(f"  python -m peon_dreame build --input-dir originals/ --output stock_voice.tar.gz")
    print(f"  python -m peon_dreame install --pack stock_voice.tar.gz --ip <IP> --token <TOKEN>")
    print(f"\nOr restore via the Dreame app: Settings → Voice Pack → default voice")


if __name__ == "__main__":
    main()
