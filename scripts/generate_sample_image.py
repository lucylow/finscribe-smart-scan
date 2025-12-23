# scripts/generate_sample_image.py
from PIL import Image, ImageDraw
im = Image.new("RGB", (600,400), (255,255,255))
draw = ImageDraw.Draw(im)
draw.text((10,10), "Sample Invoice - Replace with real image", fill=(0,0,0))
im.save("examples/sample1.jpg")

