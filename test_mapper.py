from src.app import OffsetMapper

original_text = "القصه طويل ومملل"
spelling_text = "القصة طويل وممل"

mapper = OffsetMapper(original_text, spelling_text)

# Grammar patch on spelling_text is [6:15]
# Let's see what it maps to in original text
start_orig = mapper.reverse_map_offset(6)
end_orig = mapper.reverse_map_offset(15)

print(f"Grammar patch [6:15] mapped to [{start_orig}:{end_orig}]")
print(f"Original text at [{start_orig}:{end_orig}]: '{original_text[start_orig:end_orig]}'")
