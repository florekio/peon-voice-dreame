#!/usr/bin/env python3
"""Get your Dreame robot's device info from the Dreame cloud.

Usage:
    python scripts/get_token.py
    python scripts/get_token.py --username you@email.com --region eu
"""

import argparse
import getpass
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from peon_dreame import cloud as dreame_cloud


def main():
    parser = argparse.ArgumentParser(
        description="Get your Dreame robot's device info from the Dreame cloud.",
    )
    parser.add_argument("--username", help="Dreame account email or phone")
    parser.add_argument("--region", choices=dreame_cloud.REGIONS.keys(),
                        help="Cloud server region")
    parser.add_argument("--save", action="store_true",
                        help="Save session to .dreame_session.json for use with install")
    args = parser.parse_args()

    username = args.username
    if not username:
        username = input("Dreame account email: ")

    password = getpass.getpass("Password: ")

    region = args.region
    if not region:
        print("\nServer regions:")
        for code, name in dreame_cloud.REGIONS.items():
            print(f"  {code:>3}  {name}")
        region = input("\nYour region (e.g. eu, us, cn): ").strip().lower()

    if region not in dreame_cloud.REGIONS:
        print(f"Unknown region '{region}'. Options: {', '.join(dreame_cloud.REGIONS.keys())}",
              file=sys.stderr)
        sys.exit(1)

    print(f"\nLogging in to Dreame cloud ({dreame_cloud.REGIONS[region]})...")

    try:
        session = dreame_cloud.login(username, password, region)
    except Exception as e:
        error_msg = str(e)
        print(f"\nLogin failed: {error_msg}", file=sys.stderr)
        if "invalid_user" in error_msg or "password" in error_msg:
            print("\n  Wrong email or password.", file=sys.stderr)
            print("  - Make sure this is the email/password you use in the Dreame app", file=sys.stderr)
            print("  - If you signed up via Google/Apple, you need to set a password", file=sys.stderr)
            print("    in the Dreame app first (Profile > Account Security > Password)", file=sys.stderr)
        else:
            print("\n  - Try a different region (eu, us, cn, sg, ru, kr)", file=sys.stderr)
        sys.exit(1)

    print("Login successful!\n")

    devices = dreame_cloud.get_devices(session)
    if not devices:
        print("No devices found. Try a different region.")
        sys.exit(0)

    print(f"Found {len(devices)} device(s):\n")

    for i, dev in enumerate(devices):
        name = dev.get("customName") or dev.get("deviceInfo", {}).get("displayName", "Unknown")
        model = dev.get("model", "Unknown")
        did = dev.get("did", "")
        bind_domain = dev.get("bindDomain", "")
        online = dev.get("online", False)

        print(f"  [{i+1}] {name}")
        print(f"      Model:  {model}")
        print(f"      DID:    {did}")
        print(f"      Online: {'Yes' if online else 'No'}")
        print(f"      Domain: {bind_domain}")
        print()

    if args.save or input("Save session for use with 'install --cloud'? (y/n): ").strip().lower() == "y":
        session_file = PROJECT_ROOT / ".dreame_session.json"

        # Store device info alongside session
        session["devices"] = []
        for dev in devices:
            session["devices"].append({
                "did": dev.get("did", ""),
                "model": dev.get("model", ""),
                "name": dev.get("customName") or dev.get("deviceInfo", {}).get("displayName", ""),
                "bind_domain": dev.get("bindDomain", ""),
                "online": dev.get("online", False),
            })

        session_file.write_text(json.dumps(session, indent=2))
        print(f"\nSession saved to {session_file}")
        print(f"\nTo install a voice pack:")
        print(f"  python -m peon_dreame install --cloud --pack voice.tar.gz")


if __name__ == "__main__":
    main()
