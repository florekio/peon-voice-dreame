#!/usr/bin/env python3
"""peon-dreame: Custom sound loader for Dreame X50 Ultra robot vacuum.

Replace any of the ~144 built-in sounds with your own audio files,
pushed over the local network via MiIO protocol — no root required.

Usage:
    python -m peon_dreame list-sounds
    python -m peon_dreame build --input-dir ./my-sounds/ --output voice.tar.gz
    python -m peon_dreame install --pack voice.tar.gz --ip 192.168.1.42 --token YOUR_TOKEN

To get your robot's IP and token:
    pip install python-miio
    miiocli cloud
"""

import argparse
import csv
import hashlib
import os
import re
import socket
import subprocess
import sys
import tarfile
import tempfile
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

from peon_dreame import PACKAGE_DIR, PROJECT_ROOT

SOUND_LIST_CSV = PACKAGE_DIR / "sound_list.csv"

AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".aac", ".m4a", ".wma", ".opus"}


def load_sound_list():
    """Load the sound ID → description mapping from sound_list.csv."""
    sounds = {}
    with open(SOUND_LIST_CSV, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            sounds[int(row["id"])] = row["description"]
    return sounds


def cmd_list_sounds(args):
    """Print all known sound IDs and their descriptions."""
    sounds = load_sound_list()
    print(f"{'ID':>4}  Description")
    print(f"{'--':>4}  -----------")
    for sid in sorted(sounds):
        print(f"{sid:>4}  {sounds[sid]}")
    print(f"\nTotal: {len(sounds)} sounds")


def convert_audio(input_path, output_path):
    """Convert an audio file to OGG Vorbis (16kHz, mono, loudness-normalized).

    Uses ffmpeg for resampling/loudnorm → WAV, then oggenc for Vorbis encoding.
    Falls back to ffmpeg-only with libvorbis if oggenc is not available.
    """
    wav_path = output_path.with_suffix(".wav")

    try:
        # Step 1: ffmpeg → WAV (resample, loudnorm, mono)
        ffmpeg_cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-map", "0:a",
            "-af", "loudnorm=I=-14:LRA=1:TP=-1",
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            str(wav_path),
        ]
        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  ERROR converting {input_path.name}:", file=sys.stderr)
            stderr_lines = result.stderr.strip().splitlines()
            print(f"  {stderr_lines[-1] if stderr_lines else 'Unknown error'}", file=sys.stderr)
            return False

        # Step 2: oggenc → OGG Vorbis
        oggenc_cmd = ["oggenc", "-q", "4", "-o", str(output_path), str(wav_path)]
        result = subprocess.run(oggenc_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # Fallback: try ffmpeg with libvorbis
            fallback_cmd = [
                "ffmpeg", "-y", "-i", str(wav_path),
                "-c:a", "libvorbis", "-q:a", "4",
                str(output_path),
            ]
            result = subprocess.run(fallback_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"  ERROR encoding {input_path.name} to Vorbis:", file=sys.stderr)
                stderr_lines = result.stderr.strip().splitlines()
                print(f"  {stderr_lines[-1] if stderr_lines else 'Unknown error'}", file=sys.stderr)
                return False

        return True
    finally:
        if wav_path.exists():
            wav_path.unlink()


def cmd_build(args):
    """Convert audio files and package them into a voice.tar.gz."""
    input_dir = Path(args.input_dir)
    output_path = Path(args.output)

    if not input_dir.is_dir():
        print(f"Error: {input_dir} is not a directory.", file=sys.stderr)
        sys.exit(1)

    # Check ffmpeg is available
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
    except FileNotFoundError:
        print("Error: ffmpeg not found. Install it with: brew install ffmpeg", file=sys.stderr)
        sys.exit(1)

    # Check oggenc is available (preferred Vorbis encoder)
    has_oggenc = True
    try:
        subprocess.run(["oggenc", "--version"], capture_output=True, check=True)
    except FileNotFoundError:
        has_oggenc = False
        # Check if ffmpeg has libvorbis as fallback
        result = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True)
        if "libvorbis" not in result.stdout:
            print("Error: Neither oggenc nor ffmpeg libvorbis found.", file=sys.stderr)
            print("  Install with: brew install vorbis-tools", file=sys.stderr)
            sys.exit(1)
        print("  Note: oggenc not found, using ffmpeg libvorbis as fallback.")

    # Find audio files named by sound ID
    sound_ids = load_sound_list()
    files_to_process = []
    for f in sorted(input_dir.iterdir()):
        if f.suffix.lower() not in AUDIO_EXTENSIONS:
            continue
        stem = f.stem
        if not stem.isdigit():
            print(f"  Skipping {f.name} (filename is not a numeric sound ID)")
            continue
        sid = int(stem)
        if sid not in sound_ids:
            print(f"  Warning: {f.name} — sound ID {sid} is not in the known sound list, including anyway")
        files_to_process.append((sid, f))

    if not files_to_process:
        print("Error: No valid audio files found in the input directory.", file=sys.stderr)
        print("  Files should be named by sound ID, e.g.: 0.mp3, 7.wav, 200.ogg", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(files_to_process)} audio file(s) to process.\n")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        converted = []

        for sid, input_file in files_to_process:
            ogg_name = f"{sid}.ogg"
            ogg_path = tmpdir / ogg_name
            desc = sound_ids.get(sid, "Unknown")
            print(f"  Converting {input_file.name} → {ogg_name}  ({desc})")
            if convert_audio(input_file, ogg_path):
                converted.append(ogg_path)
            else:
                print(f"  Failed to convert {input_file.name}, skipping.", file=sys.stderr)

        if not converted:
            print("Error: No files were successfully converted.", file=sys.stderr)
            sys.exit(1)

        # Package into tar.gz with .ogg files at root level
        print(f"\nPackaging {len(converted)} file(s) into {output_path}...")
        with tarfile.open(output_path, "w:gz") as tar:
            for ogg_file in converted:
                tar.add(ogg_file, arcname=ogg_file.name)

    # Compute MD5 and size
    md5_hash = hashlib.md5(output_path.read_bytes()).hexdigest()
    file_size = output_path.stat().st_size

    print(f"\nDone! Voice pack created:")
    print(f"  File:  {output_path}")
    print(f"  Size:  {file_size} bytes")
    print(f"  MD5:   {md5_hash}")


def get_local_ip(robot_ip):
    """Detect the local IP address on the same network as the robot."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to the robot's IP to determine which local interface to use
        s.connect((robot_ip, 80))
        return s.getsockname()[0]
    finally:
        s.close()


def serve_file_once(file_path, host, port, timeout=120):
    """Serve a file via HTTP. Shuts down after one successful GET or after timeout."""
    file_path = Path(file_path).resolve()
    serve_dir = file_path.parent
    filename = file_path.name
    downloaded = threading.Event()

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(serve_dir), **kw)

        def do_GET(self):
            super().do_GET()
            if self.path.lstrip("/") == filename:
                downloaded.set()

        def log_message(self, fmt, *a):
            print(f"  [HTTP] {fmt % a}")

    server = HTTPServer((host, port), Handler)
    server.timeout = 1

    def serve():
        try:
            while not downloaded.is_set():
                server.handle_request()
            # Handle a couple more requests for robustness (e.g. range requests)
            for _ in range(3):
                server.handle_request()
        except Exception:
            pass

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()

    return server, downloaded, thread


def _start_http_server(pack_path, local_ip):
    """Start an HTTP server on a random port and return (server, downloaded_event, url)."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(("", 0))
    port = server_socket.getsockname()[1]
    server_socket.close()

    url = f"http://{local_ip}:{port}/{pack_path.name}"
    server, downloaded, thread = serve_file_once(pack_path, local_ip, port)
    return server, downloaded, url


def _wait_for_download(downloaded, server):
    """Wait for the robot to download the file, then clean up."""
    print("\nWaiting for the robot to download the voice pack...")
    if downloaded.wait(timeout=120):
        print("Download complete! The robot has received the voice pack.")
    else:
        print("Timed out waiting for download. The command was sent — "
              "check if the robot received it.")
    server.server_close()


def _voice_property_params(did, voice_id, url, md5_hash, file_size):
    """Build set_properties params for voice pack install (newer Dreame models).

    Newer models (X50 Ultra, etc.) use a property write to siid=7, piid=4
    with a JSON string containing the voice pack details.
    """
    import json as _json
    value = _json.dumps({
        "id": voice_id,
        "url": url,
        "md5": md5_hash,
        "size": file_size,
    })
    return [{"did": did, "siid": 7, "piid": 4, "value": value}]


def _voice_action_params(voice_id, url, md5_hash, file_size, siid):
    """Build action params for voice pack install (older Dreame models)."""
    return {
        "did": "set_voice",
        "siid": siid,
        "aiid": 2,
        "in": [
            {"piid": 3, "value": voice_id},
            {"piid": 4, "value": url},
            {"piid": 5, "value": md5_hash},
            {"piid": 6, "value": file_size},
        ],
    }


def cmd_install(args):
    """Push a voice pack to the robot."""
    pack_path = Path(args.pack)
    if not pack_path.is_file():
        print(f"Error: {pack_path} not found.", file=sys.stderr)
        sys.exit(1)

    # Compute MD5 and size
    pack_data = pack_path.read_bytes()
    md5_hash = hashlib.md5(pack_data).hexdigest()
    file_size = len(pack_data)
    voice_id = args.voice_id
    siid = args.siid

    print(f"Voice pack: {pack_path}")
    print(f"  Size: {file_size} bytes")
    print(f"  MD5:  {md5_hash}")
    print(f"  Voice ID: {voice_id}")

    if args.cloud:
        _install_via_cloud(args, pack_path, voice_id, md5_hash, file_size, siid)
    else:
        _install_via_miio(args, pack_path, voice_id, md5_hash, file_size, siid)


def _install_via_cloud(args, pack_path, voice_id, md5_hash, file_size, siid):
    """Install voice pack via Dreame cloud API."""
    import json as json_mod
    from peon_dreame import cloud as dreame_cloud

    session_file = PROJECT_ROOT / ".dreame_session.json"
    if not session_file.exists():
        print("\nNo saved session. Run 'python scripts/get_token.py' first to log in.", file=sys.stderr)
        sys.exit(1)

    session = json_mod.loads(session_file.read_text())
    devices = session.get("devices", [])

    if not devices:
        print("No devices in saved session. Run 'python scripts/get_token.py' again.", file=sys.stderr)
        sys.exit(1)

    # Pick device
    if len(devices) == 1:
        device = devices[0]
    else:
        print("\nMultiple devices found:")
        for i, dev in enumerate(devices):
            print(f"  [{i+1}] {dev['name']} ({dev['model']})")
        choice = int(input("Select device number: ")) - 1
        device = devices[choice]

    did = device["did"]
    bind_domain = device["bind_domain"]
    print(f"\nDevice: {device['name']} ({device['model']})")
    print(f"  DID: {did}")

    # Detect local IP (use default gateway as reference since we don't know robot's IP)
    local_ip = get_local_ip("8.8.8.8")
    print(f"\nLocal IP: {local_ip}")

    # Start HTTP server
    server, downloaded, url = _start_http_server(pack_path, local_ip)
    print(f"Serving at: {url}\n")

    try:
        success = False

        # Method 1: Property write (newer models like X50 Ultra / r2532v)
        print(f"Sending set_properties command (siid=7, piid=4)...")
        prop_params = _voice_property_params(did, voice_id, url, md5_hash, file_size)
        result = dreame_cloud.send_command(session, did, bind_domain,
                                           "set_properties", prop_params)
        print(f"  Response: {result}")

        # Check result — set_properties returns a list with code per property
        result_data = result.get("data", {})
        if isinstance(result_data, dict):
            result_list = result_data.get("result", result_data)
        else:
            result_list = result_data

        prop_code = None
        if isinstance(result_list, list) and result_list:
            prop_code = result_list[0].get("code", -1)
        elif isinstance(result_list, dict):
            prop_code = result_list.get("code", -1)

        if prop_code == 0:
            print(f"  Command accepted by robot!")
            success = True
        else:
            print(f"  Property write returned code {prop_code}")

            # Method 2: Action call (older models)
            print(f"\nFalling back to action method...")
            for try_siid in [siid, 24 if siid == 7 else 7]:
                params = _voice_action_params(voice_id, url, md5_hash, file_size, try_siid)
                params["did"] = did

                print(f"  Sending action command (siid={try_siid}, aiid=2)...")
                result = dreame_cloud.send_command(session, did, bind_domain,
                                                   "action", params)
                print(f"  Response: {result}")

                action_code = result.get("data", {}).get("result", {}).get("code", -1)
                if action_code == 0:
                    print(f"  Command accepted by robot!")
                    success = True
                    break
                print(f"  Action returned code {action_code}")

        if not success:
            print(f"\nCommand may not have been accepted. Waiting for download anyway...")

        _wait_for_download(downloaded, server)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        server.server_close()
        sys.exit(1)


def _install_via_miio(args, pack_path, voice_id, md5_hash, file_size, siid):
    """Install voice pack via local MiIO protocol."""
    robot_ip = args.ip
    token = args.token

    if not robot_ip or not token:
        print("Error: --ip and --token are required for local MiIO install.", file=sys.stderr)
        print("  Or use --cloud for Dreame cloud install.", file=sys.stderr)
        sys.exit(1)

    # Detect local IP
    local_ip = get_local_ip(robot_ip)
    print(f"\nLocal IP: {local_ip}")
    print(f"Robot IP: {robot_ip}")

    # Start HTTP server
    server, downloaded, url = _start_http_server(pack_path, local_ip)
    print(f"Serving at: {url}\n")

    try:
        from miio import Device

        device = Device(ip=robot_ip, token=token)
        params = _voice_action_params(voice_id, url, md5_hash, file_size, siid)

        print(f"Sending MiIO command (siid={siid}, aiid=2)...")
        try:
            result = device.send("action", params)
            print(f"  Response: {result}")
        except Exception as e:
            if siid == 7:
                print(f"  Failed with siid=7, retrying with siid=24...")
                params["siid"] = 24
                result = device.send("action", params)
                print(f"  Response: {result}")
            else:
                raise

        _wait_for_download(downloaded, server)
    except ImportError:
        print("Error: python-miio is not installed. Run: pip install python-miio", file=sys.stderr)
        server.server_close()
        sys.exit(1)
    except Exception as e:
        print(f"Error communicating with robot: {e}", file=sys.stderr)
        server.server_close()
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        prog="peon_dreame",
        description="Custom sound loader for Dreame X50 Ultra robot vacuum.",
        epilog="To set up: python scripts/get_token.py (Dreame cloud) or miiocli cloud (Xiaomi/Mi Home)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # list-sounds
    subparsers.add_parser("list-sounds", help="Show all available sound IDs and descriptions")

    # build
    build_parser = subparsers.add_parser("build", help="Convert audio files and package into a voice pack")
    build_parser.add_argument("--input-dir", required=True, help="Directory with audio files named by sound ID (e.g. 0.mp3, 7.wav)")
    build_parser.add_argument("--output", default="voice.tar.gz", help="Output tar.gz path (default: voice.tar.gz)")

    # install
    install_parser = subparsers.add_parser("install", help="Push a voice pack to the robot")
    install_parser.add_argument("--pack", required=True, help="Path to the voice.tar.gz file")
    install_parser.add_argument("--cloud", action="store_true",
                                help="Use Dreame cloud API (run scripts/get_token.py first to log in)")
    install_parser.add_argument("--ip", help="Robot's IP address (for local MiIO mode)")
    install_parser.add_argument("--token", help="Robot's MiIO device token (for local MiIO mode)")
    install_parser.add_argument("--voice-id", default="CP", help="Voice pack ID (default: CP)")
    install_parser.add_argument("--siid", type=int, default=7, help="MiIO service ID (default: 7, try 24 if 7 fails)")

    args = parser.parse_args()

    commands = {
        "list-sounds": cmd_list_sounds,
        "build": cmd_build,
        "install": cmd_install,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
