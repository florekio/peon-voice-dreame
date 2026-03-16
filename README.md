# Peon Voice Loader for the Dreame X50 Ultra
![Image](https://github.com/user-attachments/assets/9626010a-8e0f-4b70-85af-14c568c0a788)

Custom sound loader for the **Dreame X50 Ultra** robot vacuum. Replace any of the ~190 built-in sounds (startup chime, cleaning announcements, error alerts, battery warnings, etc.) with your own audio files — pushed over your local network. No rooting, no Home Assistant, no cloud flashing required.

Comes with a **Warcraft Peon** sound pack that maps 7 iconic peon voice lines to 78 robot events. "Work, work."

## How It Works

1. **Converts** your audio files (MP3, WAV, FLAC, AAC, etc.) into the exact format the robot expects (OGG Vorbis, 16 kHz, mono, loudness-normalized)
2. **Packages** them into a `voice.tar.gz` archive
3. **Spins up** a temporary HTTP server on your machine
4. **Sends a command** to the robot (via Dreame cloud or local MiIO) telling it to download the pack
5. The robot downloads and installs the pack, then the server shuts itself down

The whole process takes about 10-30 seconds.

## Prerequisites

### Python 3.10+

```bash
python3 --version
```

### ffmpeg + oggenc

Required for audio conversion:

```bash
# macOS
brew install ffmpeg vorbis-tools

# Ubuntu / Debian
sudo apt install ffmpeg vorbis-tools

# Arch
sudo pacman -S ffmpeg vorbis-tools
```

`oggenc` (from `vorbis-tools`) is the primary Vorbis encoder. If your ffmpeg was built with `libvorbis`, it will be used as a fallback if `oggenc` is not available.

### python-miio

Only needed if using local MiIO mode (not needed for Dreame cloud mode):

```bash
pip install python-miio
```

## Setup: Connecting to Your Robot

The install command needs to talk to your robot. There are two modes depending on which app you use:

### Dreame App Users (recommended)

If your robot is set up through the **Dreame Home** app, use Dreame cloud mode. The Dreame app uses its own cloud infrastructure separate from Xiaomi's.

```bash
python scripts/get_token.py
```

This will prompt for your Dreame account email, password, and region (`eu`, `us`, `cn`, `sg`, `ru`, `kr`). It saves a session file (`.dreame_session.json`) for use with the install command.

**If you signed up via Google/Apple Sign-In**, you need to set a password first in the Dreame app: Profile > Account Security > Password.

### Mi Home App Users

If your robot is set up through **Xiaomi Mi Home**, use local MiIO mode:

```bash
pip install python-miio
miiocli cloud
```

Enter your Xiaomi account credentials. It will list your devices with their IP addresses and tokens.

## Quick Start (Peon Voice Pack)

The repo includes a mapping for 7 Warcraft Peon voice lines to 78 robot events. The sound files themselves are copyrighted by Blizzard Entertainment and must be downloaded separately:

```bash
# 1. Download peon sounds (shows instructions for where to get them)
python scripts/download_peon_sounds.py

# 2. Map peon sounds to robot sound IDs
python scripts/map_peon_sounds.py

# 3. Build the voice pack
python -m peon_dreame build --input-dir sounds/mapped/

# 4. Log in to Dreame cloud (one-time setup)
python scripts/get_token.py

# 5. Install on the robot
python -m peon_dreame install --cloud --pack voice.tar.gz
```

### Peon Sound Mapping

| Sound | Robot Events | When You'll Hear It |
|---|---|---|
| "Ready to work!" | Startup (ID 0) | Robot powers on |
| "Work, work" | All cleaning/mopping starts (30 IDs) | Every time a task begins |
| "I can do that" | Returning to dock (11 IDs) | Robot heads home to charge |
| "Be happy to" | Task completed (16 IDs) | Cleaning/mopping finished |
| "Yes?" | Confirmations (6 IDs) | "Find my robot", ding, installs |
| "Hmm?" | Paused/waiting (7 IDs) | Robot pauses or waits |
| Confused peon | Errors/stuck (7 IDs) | Robot gets stuck or errors out |

## Custom Sound Packs

### Step 1: See Available Sounds

```bash
python -m peon_dreame list-sounds
```

Prints all ~190 sound IDs and descriptions.

### Step 2: Prepare Audio Files

Create a directory with audio files **named by sound ID**:

```bash
mkdir my-sounds/
cp startup.mp3 my-sounds/0.mp3       # Startup sound
cp cleaning.wav my-sounds/7.wav       # Start cleaning
cp here-i-am.ogg my-sounds/45.ogg    # "I am here" (find robot)
cp shutdown.flac my-sounds/200.flac   # Shutdown
```

**Supported formats:** `.mp3`, `.wav`, `.ogg`, `.flac`, `.aac`, `.m4a`, `.wma`, `.opus`

You only need to include sounds you want to replace.

### Step 3: Build

```bash
python -m peon_dreame build --input-dir ./my-sounds/ --output voice.tar.gz
```

### Step 4: Install

**Dreame cloud** (Dreame app users):
```bash
python -m peon_dreame install --cloud --pack voice.tar.gz
```

**Local MiIO** (Mi Home app users):
```bash
python -m peon_dreame install --pack voice.tar.gz --ip 192.168.1.42 --token YOUR_TOKEN
```

## Backing Up Original Sounds

Before installing a custom pack, back up the stock sounds:

```bash
python scripts/backup_originals.py
```

This downloads all original English voice files from the [voicepacks_dreame](https://github.com/Makers-Im-Zigerschlitz/voicepacks_dreame) community repository into an `originals/` directory. To restore stock sounds later:

```bash
python -m peon_dreame build --input-dir originals/ --output stock_voice.tar.gz
python -m peon_dreame install --cloud --pack stock_voice.tar.gz
```

You can also restore the default voice directly in the Dreame app under Settings > Voice Pack.

## Command Reference

### `list-sounds`

```
python -m peon_dreame list-sounds
```

Prints all known sound IDs and descriptions.

### `build`

```
python -m peon_dreame build --input-dir DIR [--output FILE]
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `--input-dir` | Yes | — | Directory with audio files named by sound ID |
| `--output` | No | `voice.tar.gz` | Output path for the voice pack |

### `install`

```
python -m peon_dreame install --pack FILE [--cloud] [--ip IP] [--token TOKEN] [--voice-id ID] [--siid N]
```

| Argument | Required | Default | Description |
|---|---|---|---|
| `--pack` | Yes | — | Path to the `.tar.gz` voice pack |
| `--cloud` | No | — | Use Dreame cloud API (run `scripts/get_token.py` first) |
| `--ip` | For MiIO | — | Robot's IP address (local MiIO mode) |
| `--token` | For MiIO | — | Robot's MiIO device token (local MiIO mode) |
| `--voice-id` | No | `CP` | Voice pack identifier |
| `--siid` | No | `7` | MiIO service ID (legacy action fallback) |

### `scripts/get_token.py`

```
python scripts/get_token.py [--username EMAIL] [--region REGION]
```

Logs into the Dreame cloud, lists your devices, and saves the session for `install --cloud`.

### `scripts/download_peon_sounds.py`

```
python scripts/download_peon_sounds.py
```

Shows instructions for downloading the 7 Warcraft Peon voice lines (copyrighted by Blizzard, not included in repo).

### `scripts/map_peon_sounds.py`

```
python scripts/map_peon_sounds.py
```

Maps the 7 peon sounds in `sounds/` to 78 robot sound IDs in `sounds/mapped/`, ready for `build`.

### `scripts/backup_originals.py`

```
python scripts/backup_originals.py
```

Downloads original stock voice files into `originals/`.

## File Structure

```
peon-dreame/
├── peon_dreame/                    # Core package (python -m peon_dreame)
│   ├── __init__.py
│   ├── __main__.py                 # Entry point
│   ├── cli.py                      # Main CLI (list-sounds, build, install)
│   ├── cloud.py                    # Dreame cloud API client
│   └── sound_list.csv              # Sound ID → description mapping
├── scripts/                        # Helper scripts
│   ├── backup_originals.py         # Download stock Dreame voice files
│   ├── download_peon_sounds.py     # Instructions for downloading peon voice lines
│   ├── get_token.py                # Dreame cloud login + device discovery
│   └── map_peon_sounds.py          # Map peon sounds → robot sound IDs
├── sounds/                         # Peon source audio (not in repo — download separately)
│   └── mapped/                     # Auto-generated by map_peon_sounds.py
├── requirements.txt
├── LICENSE
└── README.md
```

## Technical Details

### Audio Conversion Pipeline

The `build` command converts each file in two steps:

1. **ffmpeg**: Resample to 16 kHz mono WAV, apply loudness normalization
2. **oggenc**: Encode to OGG Vorbis

```
ffmpeg → WAV (16kHz, mono, loudnorm) → oggenc → OGG Vorbis
```

| Parameter | Value | Why |
|---|---|---|
| Codec | Vorbis (`.ogg`) | What the robot's audio player supports |
| Sample rate | 16000 Hz | Robot speaker hardware rate |
| Channels | Mono | Single speaker |
| Loudness (I) | -14 LUFS | Comfortable for a small speaker |
| Loudness range (LRA) | 1 LU | Tight dynamic range for notifications |
| True peak (TP) | -1 dBTP | Prevents clipping |

### Voice Pack Protocol

**Newer models (X50 Ultra, r2532v, etc.)** use a property write:

```python
# Write JSON to property siid=7, piid=4
set_properties([{
    "did": "DEVICE_ID",
    "siid": 7,
    "piid": 4,
    "value": '{"id":"CP","url":"http://LOCAL_IP:PORT/voice.tar.gz","md5":"...","size":12345}'
}])
```

**Older models** use an action call with `siid=7, aiid=2` (or `siid=24, aiid=2`). The tool tries the property method first and falls back to the action method automatically.

### Dreame Cloud API

For robots registered in the Dreame Home app (not Mi Home), local MiIO is disabled. The tool communicates through Dreame's cloud instead:

- Auth: `https://{region}.iot.dreame.tech:13267/dreame-auth/oauth/token`
- Commands: `https://{region}.iot.dreame.tech:13267/dreame-iot-com-{host}/device/sendCommand`

The robot still downloads the voice pack directly from your local HTTP server — only the "go download this" instruction goes through the cloud.

## Networking Requirements

Your computer and the robot **must be on the same local network**. During install:

1. Your computer starts a temporary HTTP server on a random port
2. The robot receives the download URL (pointing to your computer's LAN IP)
3. The robot makes an HTTP GET request to your computer to download the `.tar.gz`

This means your computer must accept an **incoming connection** from the robot.

### Firewall Configuration

If the robot can't download the voice pack ("timed out waiting for download"), your firewall may be blocking the incoming connection.

**macOS:**

- If the macOS firewall is enabled (System Settings > Network > Firewall), you may see a dialog: _"Do you want the application 'Python' to accept incoming network connections?"_ — click **Allow**.
- If you don't see the dialog, either temporarily disable the firewall or add Python to the allowed apps:

  ```bash
  # Check firewall status
  /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate

  # Add Python to allowed apps (requires sudo)
  sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /usr/local/bin/python3
  sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp /usr/local/bin/python3
  ```

  Or find your Python path with `which python3` and use that instead.

**Linux (iptables/nftables):**

The HTTP server uses a random port. If you have a restrictive firewall, temporarily open a range or disable it:

```bash
# Option A: temporarily allow all incoming on the local network
sudo iptables -A INPUT -s 192.168.0.0/16 -j ACCEPT

# Option B: disable firewall temporarily
sudo ufw disable        # Ubuntu
sudo systemctl stop firewalld  # Fedora/RHEL
```

**Windows:**

Windows Defender Firewall will prompt you to allow Python through the firewall when the HTTP server starts. Click **Allow access** and make sure "Private networks" is checked.

### Router / AP Isolation

Some routers have **AP isolation** or **client isolation** enabled, which prevents devices on the same Wi-Fi network from talking to each other. If the robot can't reach your computer:

- Check your router settings for "AP Isolation", "Client Isolation", or "Wireless Isolation" and disable it
- If your computer is on Ethernet and the robot is on Wi-Fi (or vice versa), make sure they're on the same subnet and that inter-VLAN routing is allowed
- Try temporarily connecting your computer to the same Wi-Fi network the robot uses

### Same Subnet Check

Verify both devices are on the same network:

```bash
# Your computer's IP
ifconfig | grep "inet " | grep -v 127.0.0.1

# The robot's IP (visible in the Dreame app under device settings)
ping 192.168.178.XX
```

Both should be in the same range (e.g., `192.168.178.x`).

## Troubleshooting

### "Error: ffmpeg not found" / "oggenc not found"

```bash
brew install ffmpeg vorbis-tools   # macOS
sudo apt install ffmpeg vorbis-tools  # Debian/Ubuntu
```

### Dreame cloud login fails

- Make sure you're using the email/password from the **Dreame app** (not Mi Home)
- If you signed up via Google/Apple, set a password in the app first
- Try different regions (`eu`, `us`, `cn`, etc.)

### "Timed out waiting for the robot to download"

The command was accepted but the robot couldn't reach your HTTP server. Check:

1. **Firewall** — see [Firewall Configuration](#firewall-configuration) above
2. **Same network** — computer and robot must be on the same subnet
3. **AP isolation** — check router settings (see [Router / AP Isolation](#router--ap-isolation))
4. **VPN** — if you're on a VPN, your local IP may not be reachable from the robot. Disconnect the VPN and try again.

### Robot plays the old sounds after installing

- Restart the robot (power cycle or via the app)
- In the Dreame app, check Settings > Voice Pack — make sure it's not set to a built-in voice that overrides the custom pack

### Robot returned code -2

The command format doesn't match your model. The tool tries the newer property-write method first (works on X50 Ultra and other recent models), then falls back to the legacy action method. If both fail, your model may need a different siid — check the [MiOT spec](https://home.miot-spec.com/) for your model.

## Tips

- **Test with "Find Robot"**: Sound ID 45 is triggered by the "find my robot" feature in the Dreame app — quick way to test without running a cleaning cycle
- **Keep sounds short**: 1-3 seconds works best. Longer sounds may get cut off.
- **ID 274 (Ding)** fires frequently — fun to customize
- **Backup first**: Run `python scripts/backup_originals.py` before your first custom install

## Credits

- Sound list from [voicepacks_dreame](https://github.com/Makers-Im-Zigerschlitz/voicepacks_dreame) by Makers Im Zigerschlitz
- Dreame cloud API reverse-engineered by [Tasshack/dreame-vacuum](https://github.com/Tasshack/dreame-vacuum) and [TA2k/ioBroker.dreame](https://github.com/TA2k/ioBroker.dreame)
- MiIO protocol via [python-miio](https://github.com/rytilahti/python-miio)

## License

MIT
