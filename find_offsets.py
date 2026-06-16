#!/usr/bin/env python3
# find_offsets.py - Find correct character offsets for the test text

text = "ذهبو الى المدرسة ثم ذهبو الى البيت ثم ذهبو مرة اخرى"

print(f"Text: {text}")
print(f"Length: {len(text)} characters\n")

# Find all occurrences of "ذهبو"
word = "ذهبو"
print(f'Finding all occurrences of "{word}":\n')

start = 0
occurrence = 1
offsets = []

while True:
    pos = text.find(word, start)
    if pos == -1:
        break
    end = pos + len(word)
    offsets.append((pos, end))
    print(f"Occurrence {occurrence}: [{pos}:{end}] = '{text[pos:end]}'")
    start = pos + 1
    occurrence += 1

print(f"\nCorrect test offsets:")
print([{"start": start, "end": end, "original": "ذهبو", "correction": "ذهبوا", "type": "spelling"} for start, end in offsets])
