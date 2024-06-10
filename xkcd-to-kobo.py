#!/usr/bin/env python

from datetime import datetime
import io
from jinja2 import Environment, PackageLoader, select_autoescape
import json
import os
from PIL import Image, ImageFont, ImageDraw
import requests
import shutil
import sys
from pathlib import Path
from multiprocessing import Pool
from zipfile import ZipFile

jinja_env = Environment(
    loader=PackageLoader("xkcd-to-kobo"), autoescape=select_autoescape()
)

comic_template = jinja_env.get_template("comic.html.j2")

total_comics = int(os.environ.get("XKCD_TOTAL_COMICS", "300"))
cache_path = Path(os.environ.get("XKCD_CACHE_DIR", "cache"))
output_dir = Path(os.environ.get("XKCD_OUTPUT_DIR", "xkcd.kepub.epub"))

if len(sys.argv) > 1:
    output_dir = Path(sys.argv[1])

if not cache_path.exists():
    cache_path.mkdir()


def fetch_comic(comic_number):
    print("Fetching comic #{}...".format(comic_number))
    metadata_path = cache_path / "{}.json".format(comic_number)

    try:
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        else:
            metadata = requests.get(
                "https://xkcd.com/{}/info.0.json".format(comic_number)
            ).json()
            metadata_path.write_text(json.dumps(metadata), encoding="utf-8")
    except:
        metadata = {
            "title": "Error",
            "alt": "There was an error fetching this comic",
            "img": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
        }

    image_path = cache_path / "{}.png".format(comic_number)
    image_is_2x = False
    try:
        if not image_path.exists():
            try:
                # Try to download the 2x version of the image
                response = requests.get(
                    "{}_2x.png".format(metadata["img"].removesuffix(".png"))
                )
                response.raise_for_status()
                image = response.content
                image_is_2x = True
            except:
                image = requests.get(metadata["img"]).content
            image_path.write_bytes(image)

        with Image.open(image_path) as img:
            width, height = img.size

        if image_is_2x:
            width //= 2
            height //= 2
    except:
        # Use placeholder transparent pixel if image is not available
        shutil.copy("assets/placeholder.png", image_path)
        width = 1
        height = 1

    html = comic_template.render(
        number=comic_number,
        title=metadata["title"],
        alt=metadata["alt"],
        image_path=image_path.name,
        width=width,
        height=height,
    )

    return {
        "number": comic_number,
        "title": metadata["title"],
        "alt": metadata["alt"],
        "image_path": image_path,
        "html": html,
    }


def main():
    latest_metadata = requests.get("https://xkcd.com/info.0.json").json()
    latest_comic_number = latest_metadata["num"]
    latest_metadata_path = cache_path / "{}.json".format(latest_comic_number)
    latest_metadata_path.write_text(json.dumps(latest_metadata), encoding="utf-8")

    first = max(1, latest_comic_number - total_comics + 1)
    last = latest_comic_number

    if total_comics < 1:
        first = 1

    if (cache_path / "run.json").exists():
        last_run_metadata = json.loads((cache_path / "run.json").read_text())
        if (
            last_run_metadata.get("first", -1) == first
            and last_run_metadata.get("last", -1) == last
        ):
            print("No new comics to fetch, using cached output")
            shutil.copy(cache_path / "output.kepub.epub", output_dir)
            return

    with Pool(32) as p:
        comics = p.map(
            fetch_comic,
            range(last, first, -1),
        )

    print("Generating kepub...")
    with ZipFile(str(cache_path / "output.kepub.epub"), "w") as container:
        container.writestr("mimetype", "application/epub+zip", compress_type=0)
        container.write("assets/container.xml", "META-INF/container.xml")
        container.write(
            "assets/com.apple.ibooks.display-options.xml",
            "META-INF/com.apple.ibooks.display-options.xml",
        )
        container.write("assets/cover.jpg", "OEBPS/cover.jpg")
        container.write("assets/style.css", "OEBPS/style.css")
        container.write("assets/xkcd-script.ttf", "OEBPS/xkcd-script.ttf")

        container.writestr(
            "OEBPS/content.opf",
            jinja_env.get_template("content.opf.xml.j2").render(
                comics=comics, first=first, last=last, time=datetime.now().isoformat()
            ),
        )
        container.writestr(
            "OEBPS/toc.ncx",
            jinja_env.get_template("toc.ncx.xml.j2").render(
                comics=comics, first=first, last=last
            ),
        )
        container.writestr(
            "OEBPS/nav.xhtml",
            jinja_env.get_template("nav.html.j2").render(
                comics=comics, first=first, last=last
            ),
        )

        for comic in comics:
            container.write(
                comic["image_path"], "OEBPS/{}".format(comic["image_path"].name)
            )
            container.writestr("OEBPS/{}.xhtml".format(comic["number"]), comic["html"])

    shutil.copy(cache_path / "output.kepub.epub", output_dir)
    (cache_path / "run.json").write_text(json.dumps({"first": first, "last": last}))


if __name__ == "__main__":
    main()
