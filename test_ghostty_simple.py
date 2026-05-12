#!/usr/bin/env python3
"""
Minimal Ghostty Graphics Test - NO dependencies
Run this directly in your Ghostty shell:
  cd /Users/rhelmer/src/attribution-mcp
  python3 test_ghostty_simple.py
"""
import base64
import sys
from io import BytesIO

# Create a SMALL test image using raw PNG bytes
# 50x50 green square with white text would be ideal,
# but let's use the absolute minimal approach
try:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (400, 100), "#1a1a2e")
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 390, 90], fill="#4CAF50")
    draw.rectangle([15, 15, 385, 85], fill="#1a1a2e")
    draw.text((100, 35), "GHOSTTY IMAGE TEST", fill="#4CAF50")
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    img_data = buf.read()
    print(f"Created image: {len(img_data)} bytes")
except ImportError:
    # Minimal raw PNG if PIL not available
    print("PIL not available, using minimal test")
    img_data = b'\x89PNG\r\n\x1a\n' + b'\x00' * 100
    print(f"Minimal image: {len(img_data)} bytes (invalid)")

# Encode
b64 = base64.b64encode(img_data).decode("ascii")
print(f"Base64 length: {len(b64)} chars")

# Print what we're about to send
print(f"\n--- ESCAPE SEQUENCE ---")
print(f"Starting: \\x1b_Ga=t,t=d,f=100,q=2;")
print(f"Data: {len(b64)} base64 chars")
print(f"Ending: \\x1b\\\\")
print(f"--- END ---\n")

# Method 1: Single chunk, standard approach
print("Method 1: Standard single chunk")
sys.stdout.write("\x1b_Ga=t,t=d,f=100,q=2;")
sys.stdout.write(b64)
sys.stdout.write("\x1b\\")
sys.stdout.flush()
print("\nSent! Do you see a green image above?")

# Wait for user feedback
input("\nPress Enter for Method 2...")

# Method 2: With size specification
print("\nMethod 2: With explicit size (50x12 cells)")
sys.stdout.write("\x1b_Ga=t,t=d,f=100,s=50x12,q=2;")
sys.stdout.write(b64)
sys.stdout.write("\x1b\\")
sys.stdout.flush()
print("\nSent! Do you see it?")

input("\nPress Enter for Method 3...")

# Method 3: Without quiet mode
print("\nMethod 3: Without quiet (q=1)")
sys.stdout.write("\x1b_Ga=t,t=d,f=100,q=1;")
sys.stdout.write(b64)
sys.stdout.write("\x1b\\")
sys.stdout.flush()
print("\nSent! (Terminal may have sent a response)")

input("\nPress Enter for Method 4...")

# Method 4: Different escape sequence terminator
print("\nMethod 4: String terminator (ST = \\x9c)")
sys.stdout.write("\x1b_Ga=t,t=d,f=100,q=2;")
sys.stdout.write(b64)
sys.stdout.write("\x9c")
sys.stdout.flush()
print("\nSent! (Used 0x9c instead of ESC \\)")

input("\nPress Enter for Method 5...")

# Method 5: Try with image ID
print("\nMethod 5: With image ID=42")
sys.stdout.write("\x1b_Ga=t,t=d,f=100,i=42,q=2;")
sys.stdout.write(b64)
sys.stdout.write("\x1b\\")
sys.stdout.flush()
print("\nSent!")

print("\n" + "="*60)
print("Done! Which methods showed images?")
print("="*60)
