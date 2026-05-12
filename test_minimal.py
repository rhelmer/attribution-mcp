#!/usr/bin/env python3
"""Absolute minimal test - no PIL, no libs"""
import sys, os

print(f"TERM={os.environ.get('TERM','?')}")
print(f"TERM_PROGRAM={os.environ.get('TERM_PROGRAM','?')}")
print(f"Is tty: {sys.stdin.isatty()}")
print()

# Raw escape sequence for kitty graphics
# \x1b_G = ESC _ G (start graphics command)
# a=t,t=d,f=100 = transmit, direct, PNG format
# q=2 = quiet mode
# ; = separator
# <base64 data>
# \x1b\ = ESC \ (string terminator)

test = b'\x1b_Ga=t,t=d,f=100,q=2;'
test += b'aW1hZ2UgdGVzdA=='  # tiny base64
test += b'\x1b\\'

# Write raw bytes to stdout (not through string encoding)
sys.stdout.buffer.write(test)
sys.stdout.buffer.flush()

print("Sent minimal sequence")
