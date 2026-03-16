#!/usr/bin/env python3
"""Map peon sound files to Dreame X50 Ultra sound IDs.

Creates a directory of ID-named copies ready to feed into:
    python -m peon_dreame build --input-dir sounds/mapped/

Each peon sound is matched to the Dreame events where it fits thematically.
"""

import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOUNDS_DIR = PROJECT_ROOT / "sounds"
OUTPUT_DIR = SOUNDS_DIR / "mapped"

# Peon sound → list of Dreame sound IDs
MAPPING = {
    # "Ready to work!" — startup/boot
    "ready-to-work.mp3": [
        0,    # Startup sound
    ],

    # "Work, work" — all task-start events
    "work-work.mp3": [
        7,    # Start cleaning
        8,    # Start spot cleaning
        9,    # Start scheduled cleaning
        10,   # Start resuming cleaning
        56,   # Start selected room cleaning
        57,   # Start zoned cleaning
        58,   # Proceed with cleaning task
        61,   # Start mopping
        62,   # Start remote control cleaning
        76,   # Spot cleanup is starting
        82,   # Start mapping
        83,   # Proceed with mapping
        90,   # Proceed with cleaning task
        105,  # Start cleaning
        106,  # Start cleaning the mop
        110,  # Start auto empty
        126,  # Start cleaning
        127,  # Start spot cleaning
        128,  # Start spot mopping
        129,  # Start scheduled cleaning
        130,  # Start scheduled mopping
        131,  # Start spot cleaning
        132,  # Start spot mopping
        133,  # Start selected room cleaning
        134,  # Start selected room mopping
        135,  # Start zoned cleaning
        136,  # Start zoned mopping
        137,  # Resume cleaning
        138,  # Resume mopping
        280,  # Start custom cleaning
    ],

    # "I can do that" — returning to dock / going somewhere
    "i-can-do-that.mp3": [
        13,   # Returning to the dock to charge
        15,   # I'm about to return to the starting point
        48,   # Low battery. Returning to the dock
        55,   # Positioning succeeded. Resuming returning to the dock
        65,   # Resume returning to the dock
        87,   # Low battery. Returning to the dock
        139,  # Resume returning to the base for self-cleaning
        148,  # Return to the base for self-cleaning
        155,  # Start to return to the charging and mop cleaning dock
        177,  # Leaving the base station
        188,  # Automatic docking engaged
    ],

    # "Be happy to" — task completed / success
    "be-happy-to.mp3": [
        5,    # Network connected successfully
        12,   # Cleaning task completed
        28,   # Updated successfully
        54,   # Positioning succeeded. Resuming cleaning
        59,   # Mopping completed
        84,   # Mapping completed
        85,   # Positioning succeeded. Proceeding with mapping
        103,  # Mop pad wash board installed. Robot resumes working
        113,  # Task completed
        143,  # Cleaning completed
        144,  # Mopping completed
        145,  # Positioning successful. Resume cleaning
        146,  # Positioning successful. Resume mopping
        164,  # Task ends
        169,  # Mop pad drying complete
        264,  # Task complete
    ],

    # "Yes?" — acknowledgment / confirmation / I'm here
    "yes.mp3": [
        23,   # Water tank has been installed
        45,   # I am here
        114,  # Mop pads installed
        244,  # Detergent bottle installed
        274,  # Ding sound
        293,  # Calling enabled
    ],

    # "Hmm?" — paused / waiting / thinking
    "hmm.mp3": [
        11,   # Paused
        20,   # Low battery
        30,   # Positioning please wait
        122,  # Continuous positioning please wait
        140,  # New environment detected
        154,  # Operated too frequently
        187,  # It will take about 5 to 10 minutes
    ],

    # Confused/annoyed — errors / stuck / problems / shutdown
    "something-you-re-doing.mp3": [
        40,   # Robot stuck
        44,   # Error
        69,   # Cleanup path blocked
        149,  # Unable to reach the specified area
        151,  # The path is blocked
        200,  # Shutdown sound
        262,  # Self-positioning failed
    ],
}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Clean previous mapped files
    for f in OUTPUT_DIR.glob("*.mp3"):
        f.unlink()

    total = 0
    for sound_file, ids in MAPPING.items():
        src = SOUNDS_DIR / sound_file
        if not src.exists():
            print(f"  WARNING: {sound_file} not found in {SOUNDS_DIR}, skipping")
            continue
        for sid in ids:
            dst = OUTPUT_DIR / f"{sid}.mp3"
            shutil.copy2(src, dst)
            total += 1
        print(f"  {sound_file} → {len(ids)} sound IDs: {ids}")

    print(f"\nMapped {total} files into {OUTPUT_DIR}/")
    print(f"\nNext step:")
    print(f"  python -m peon_dreame build --input-dir {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
