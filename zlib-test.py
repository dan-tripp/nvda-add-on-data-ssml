#!/usr/bin/env python3

import sys, os, re, subprocess, zlib

os.chdir(os.path.dirname(sys.argv[0]))

#dictionary = b"common phrases and substrings here"
dictionary = "common phrases and abcdefghijklmnopqrxtuvqxysfkhsfkjhfkshdkjfhskfdshkjshf here".encode('utf-8')

compressor = zlib.compressobj(level=9, zdict=dictionary, wbits=-15)
#compressor = zlib.compressobj(level=9)
your_string = 'abcdefghijklmnopqrxtuvqxysfkhsfkjhfkshdkjfhskfdshkjshf ph S U Veez'.encode('utf-8')
compressed = compressor.compress(your_string) + compressor.flush()
print(f'compressed: {len(compressed)} {compressed}')

# Decompress with:
decompressor = zlib.decompressobj(zdict=dictionary, wbits=-15)
original = decompressor.decompress(compressed)

