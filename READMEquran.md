# Bayan Search API

## Supported Languages

The `search_bayan()` function supports the following values for the `target_type` parameter:

```python
languages = [
    "تدقيق الايات",
    "english",
    "french",
    "turkish",
    "persian",
    "urdu",
    "russian",
    "spanish",
    "german",
    "indonesian",
    "malay",
    "bengali",
    "bosnian",
    "portuguese",
    "uzbek"
]
```

## Language Descriptions

| Value        | Output                                |
| ------------ | ------------------------------------- |
| تدقيق الايات | Quran text in Uthmani script (Arabic) |
| english      | English translation                   |
| french       | French translation                    |
| turkish      | Turkish translation                   |
| persian      | Persian (Farsi) translation           |
| urdu         | Urdu translation                      |
| russian      | Russian translation                   |
| spanish      | Spanish translation                   |
| german       | German translation                    |
| indonesian   | Indonesian translation                |
| malay        | Malay translation                     |
| bengali      | Bengali translation                   |
| bosnian      | Bosnian translation                   |
| portuguese   | Portuguese translation                |
| uzbek        | Uzbek translation                     |

## Example Usage

```python
result = search_bayan(
    "ولله المشرق والمغرب فأينما تولوا فثم وجه الله",
    target_type="english"
)

print(result["matched_segment"])
print(result["full_verse"])
```

## Notes

* If `target_type` is omitted, the default value is `"تدقيق الايات"`.
* The search engine supports fuzzy matching and can handle minor spelling mistakes.
* Quranic Uthmani text is returned when using `"تدقيق الايات"`.
* Translations are returned when using any of the supported language names above.