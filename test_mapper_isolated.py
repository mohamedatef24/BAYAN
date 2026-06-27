import difflib

class OffsetMapper:
    def __init__(self, text_before, text_after):
        self._text_before = text_before
        self._text_after = text_after
        self._opcodes = []
        s = difflib.SequenceMatcher(None, self._text_before, self._text_after)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            self._opcodes.append((tag, i1, i2, j1, j2))

    def reverse_map_offset(self, pos_in_after, is_end=False):
        """Map a single position from text_after → text_before."""
        # Find all opcodes where the position falls inside [j1, j2]
        matches = []
        for tag, i1, i2, j1, j2 in self._opcodes:
            if j1 <= pos_in_after <= j2:
                matches.append((tag, i1, i2, j1, j2))
                
        if not matches:
            return len(self._text_before)
            
        # If there's an ambiguity (multiple opcodes touch this point),
        # or if the point falls exactly on the boundary of a deletion.
        
        # Calculate the mapped position for each match
        mapped_positions = []
        for tag, i1, i2, j1, j2 in matches:
            if j2 == j1:  # insertion point in text_before (deleted in text_after)
                # If it's a deletion, the position in before spans [i1, i2].
                # If we're mapping an 'end' coordinate, we want to encompass the deleted text (i2).
                # If we're mapping a 'start' coordinate, we want the start of the deletion (i1).
                mapped_positions.append(i2 if is_end else i1)
            else:
                ratio = (pos_in_after - j1) / (j2 - j1)
                mapped_positions.append(round(i1 + ratio * (i2 - i1)))
                
        # If is_end is True, we want to maximize the mapped offset (include as much as possible)
        # If is_end is False, we want to minimize the mapped offset
        return max(mapped_positions) if is_end else min(mapped_positions)

original_text = "القصه طويل ومملل" # len 16
spelling_text = "القصة طويل وممل"  # len 15

mapper = OffsetMapper(original_text, spelling_text)

start_orig = mapper.reverse_map_offset(6, is_end=False)
end_orig = mapper.reverse_map_offset(15, is_end=True)

print(f"Grammar patch [6:15] maps to [{start_orig}:{end_orig}]")
print(f"Original text at mapped coords: '{original_text[start_orig:end_orig]}'")
