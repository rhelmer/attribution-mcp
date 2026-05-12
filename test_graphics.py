#!/usr/bin/env python3
"""
Minimal test for kitty graphics protocol in Ghostty.
"""

import base64
import sys
from io import BytesIO
from PIL import Image, ImageDraw


def create_test_image(width=400, height=200):
    """Create a simple test image with text."""
    img = Image.new("RGB", (width, height), "#1a1a2e")
    draw = ImageDraw.Draw(img)

    # Draw a gradient bar
    for x in range(width):
        r = int(255 * x / width)
        g = int(100 * (1 - x / width))
        b = 150
        draw.line([(x, 50), (x, 150)], fill=(r, g, b))

    # Draw text
    try:
        from PIL import ImageFont
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 24)
    except:
        font = ImageFont.load_default()

    draw.text((80, 20), "KITTY GRAPHICS TEST", fill="#ffffff", font=font)
    draw.text((120, 160), "SUCCESS!", fill="#4CAF50", font=font)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.read()


def test_basic():
    """Method 1: Basic single-chunk transfer."""
    print("\n[TEST 1] Basic single-chunk image transfer")
    print("-" * 50)

    img_data = create_test_image()
    b64 = base64.b64encode(img_data).decode("ascii")

    # Correct kitty graphics escape sequence: a=t,t=d,f=100
    sys.stdout.write("\x1b_Ga=t,t=d,f=100,q=2;")
    sys.stdout.write(b64)
    sys.stdout.write("\x1b\\")
    sys.stdout.flush()

    print("\n[TEST 1] Sent")
    input("\nPress Enter to continue...")


def test_with_id():
    """Method 2: With image ID and quiet mode."""
    print("\n[TEST 2] Image with ID")
    print("-" * 50)

    img_data = create_test_image()
    b64 = base64.b64encode(img_data).decode("ascii")

    sys.stdout.write("\x1b_Ga=t,t=d,f=100,i=99,q=2;")
    sys.stdout.write(b64)
    sys.stdout.write("\x1b\\")
    sys.stdout.flush()

    print("\n[TEST 2] Sent")
    input("\nPress Enter to continue...")


def test_with_size():
    """Method 3: With explicit size in cells."""
    print("\n[TEST 3] With size=40x15 cells")
    print("-" * 50)

    img_data = create_test_image()
    b64 = base64.b64encode(img_data).decode("ascii")

    sys.stdout.write("\x1b_Ga=t,t=d,f=100,s=40x15,q=2;")
    sys.stdout.write(b64)
    sys.stdout.write("\x1b\\")
    sys.stdout.flush()

    print("\n[TEST 3] Sent")
    input("\nPress Enter to continue...")


def test_chunked():
    """Method 4: Chunked transfer."""
    print("\n[TEST 4] Chunked transfer")
    print("-" * 50)

    img_data = create_test_image(600, 300)
    b64 = base64.b64encode(img_data).decode("ascii")

    # Split into chunks
    chunk_size = 2000
    chunks = [b64[i:i+chunk_size] for i in range(0, len(b64), chunk_size)]

    print(f"  Total base64 length: {len(b64)}")
    print(f"  Number of chunks: {len(chunks)}")

    for idx, chunk in enumerate(chunks):
        is_last = idx == len(chunks) - 1
        m = "0" if is_last else "1"

        if idx == 0:
            sys.stdout.write(f"\x1b_Ga=t,t=d,f=100,m={m},i=100;{chunk}\x1b\\")
        else:
            sys.stdout.write(f"\x1b_Gm={m},i=100;{chunk}\x1b\\")

        print(f"  Sent chunk {idx+1}/{len(chunks)}")

    sys.stdout.flush()

    print("\n[TEST 4] Sent")
    input("\nPress Enter to continue...")


def test_probe():
    """Method 5: Probe for support."""
    print("\n[TEST 5] Probe for kitty graphics support")
    print("-" * 50)

    sys.stdout.write("\x1b_Gi=1,a=q\x1b\\")
    sys.stdout.flush()

    print("  Probe sent - check for response")
    input("\nPress Enter to continue...")


def main():
    print("=" * 60)
    print(" KITTY GRAPHICS PROTOCOL TEST")
    print("=" * 60)
    print(f"\n Terminal: {sys.stdin.isatty() and 'interactive' or 'not interactive'}")
    print(" Make sure you're running this in Ghostty/kitty/WezTerm")

    test_basic()
    test_with_id()
    test_with_size()
    test_chunked()
    test_probe()

    print("\n" + "=" * 60)
    print(" All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
