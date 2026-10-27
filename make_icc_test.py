from PIL import Image, ImageCms, ImageDraw

image = Image.new(
    "RGB",
    (1200, 800),
    (240, 240, 240),
)

draw = ImageDraw.Draw(image)

draw.rectangle(
    (100, 100, 500, 700),
    fill=(220, 40, 40),
)

draw.rectangle(
    (500, 100, 900, 700),
    fill=(40, 180, 60),
)

draw.rectangle(
    (900, 100, 1100, 700),
    fill=(40, 80, 220),
)

srgb_profile = ImageCms.ImageCmsProfile(
    ImageCms.createProfile(
        "sRGB"
    )
).tobytes()

image.save(
    "icc_test_srgb.jpg",
    "JPEG",
    quality=100,
    subsampling=0,
    icc_profile=srgb_profile,
)

print("icc_test_srgb.jpg を作成しました")
