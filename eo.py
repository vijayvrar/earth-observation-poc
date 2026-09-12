import os
import earthaccess
import rasterio
import numpy as np
from rasterio.warp import transform
from rasterio.windows import Window


def get_satellite_image(latitude, longitude):

    # 1. Login
    auth = earthaccess.login(strategy="environment")

    if not auth.authenticated:
        raise Exception("NASA Earthdata authentication failed.")

    # 2. Search HLS Sentinel-2
    granules = earthaccess.search_data(
        short_name="HLSS30",
        point=(longitude, latitude),
        temporal=("2026-01-01", "2026-12-31"),
        cloud_cover=(0, 20),
        count=10
    )

    if not granules:
        raise Exception("No suitable satellite data found.")

    # 3. Select first observation
    granule = granules[0]

    granule_id = granule["umm"]["GranuleUR"]

    temporal_info = granule["umm"]["TemporalExtent"]["RangeDateTime"]
    start_time = temporal_info["BeginningDateTime"]

    # 4. Find RGB bands
    blue_link = None
    green_link = None
    red_link = None

    for link in granule.data_links():

        if ".B02.tif" in link:
            blue_link = link

        elif ".B03.tif" in link:
            green_link = link

        elif ".B04.tif" in link:
            red_link = link

    if not blue_link or not green_link or not red_link:
        raise Exception("Required RGB bands are missing.")

    # 5. Create folders
    os.makedirs("data", exist_ok=True)
    os.makedirs("static/outputs", exist_ok=True)

    # 6. Download bands
    downloaded_files = earthaccess.download(
        [blue_link, green_link, red_link],
        local_path="data"
    )

    # 7. Identify downloaded files
    blue_file = None
    green_file = None
    red_file = None

    for file in downloaded_files:

        file = str(file)

        if ".B02." in file:
            blue_file = file

        elif ".B03." in file:
            green_file = file

        elif ".B04." in file:
            red_file = file

    if not blue_file or not green_file or not red_file:
        raise Exception("Downloaded RGB files could not be identified.")

    # 8. Calculate the 500 x 500 pixel window

    crop_size = 500
    half = crop_size // 2

    with rasterio.open(red_file) as src:

        # Convert user's WGS84 coordinate
        # into the image's coordinate system
        x, y = transform(
            "EPSG:4326",
            src.crs,
            [longitude],
            [latitude]
        )

        image_x = x[0]
        image_y = y[0]

        # Convert projected coordinate to pixel
        row, col = src.index(image_x, image_y)

        # Make sure the window stays inside the image
        row_start = max(0, row - half)
        row_end = min(src.height, row + half)

        col_start = max(0, col - half)
        col_end = min(src.width, col + half)

        window = Window(
            col_start,
            row_start,
            col_end - col_start,
            row_end - row_start
        )

        # Read ONLY the required area
        red = src.read(1, window=window)

    with rasterio.open(green_file) as src:
        green = src.read(1, window=window)

    with rasterio.open(blue_file) as src:
        blue = src.read(1, window=window)

    # 9. Combine RGB
    rgb_crop = np.dstack(
        (red, green, blue)
    ).astype(float)

    # 10. Visualization enhancement
    rgb_display = rgb_crop.copy()

    rgb_display[rgb_display < 0] = 0

    valid = rgb_display[rgb_display > 0]

    if len(valid) == 0:
        raise Exception("No valid pixels found.")

    low = np.percentile(valid, 2)
    high = np.percentile(valid, 98)

    if high <= low:
        raise Exception("Unable to enhance image: insufficient pixel range.")

    rgb_display = np.clip(
        (rgb_display - low) / (high - low),
        0,
        1
    )

    gamma = 0.7

    rgb_display = np.power(
        rgb_display,
        gamma
    )

    # 11. Save image
    output_file = "static/outputs/sentinel_image.png"

    import matplotlib.pyplot as plt

    plt.figure(figsize=(10, 10))

    plt.imshow(rgb_display)

    plt.axis("off")

    plt.savefig(
        output_file,
        dpi=150,
        bbox_inches="tight"
    )

    plt.close()

    # 12. Return information to Flask
    return {
        "image": "/static/outputs/sentinel_image.png",
        "observation": start_time,
        "granule": granule_id,
        "latitude": latitude,
        "longitude": longitude
    }
