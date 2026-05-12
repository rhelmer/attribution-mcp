#!/usr/bin/env python3
"""
Ghostty Graphics Debug - Show exact bytes being sent
Run this IN YOUR GHOSTTY SHELL
"""
import base64, sys, os
from io import BytesIO

print(f"TERM={os.environ.get('TERM')}")
print(f"TERM_PROGRAM={os.environ.get('TERM_PROGRAM')}")
print()

# Create test image
from PIL import Image, ImageDraw
img = Image.new("RGB", (300, 100), "#4CAF50")
draw = ImageDraw.Draw(img)
draw.text((60, 35), "TEST", fill="white")
buf = BytesIO()
img.save(buf, format="PNG")
img_bytes = buf.getvalue()
b64 = base64.b64encode(img_bytes).decode("ascii")

# Method A: Standard ESC \ terminator
print("=== METHOD A: ESC \\ terminator ===")
seq_a = f"\x1b_Ga=t,t=d,f=100,q=2;{b64}\x1b\\"
sys.stdout.write(seq_a)
sys.stdout.flush()
print(f"\nSent {len(seq_a)} chars")

# Method B: 0x9c terminator
print("\n=== METHOD B: 0x9c terminator ===")
seq_b = f"\x1b_Ga=t,t=d,f=100,q=2;{b64}\x9c"
sys.stdout.write(seq_b)
sys.stdout.flush()
print(f"\nSent {len(seq_b)} chars")

# Method C: Raw bytes
print("\n=== METHOD C: Raw bytes via buffer ===")
header = b"\x1b_Ga=t,t=d,f=100,q=2;"
footer = b"\x1b\\"
full = header + b64.encode() + footer
sys.stdout.buffer.write(full)
sys.stdout.buffer.flush()
print(f"\nSent {len(full)} bytes")

print("\n=== DONE ===")
print("Did ANY method show an image?")
