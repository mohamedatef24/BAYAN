"""Generate extension icons from LOGOS/1.png (gradient bg for best small-size visibility)."""
from PIL import Image

img = Image.open("LOGOS/1.png")
for size in [16, 32, 48, 128]:
    img.resize((size, size), Image.LANCZOS).save(f"extension/assets/icons/icon{size}.png")
    print(f"Generated icon{size}.png ({size}x{size}) from LOGOS/1.png")
print("Done!")
