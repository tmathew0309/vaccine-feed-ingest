#!/usr/bin/env python3

import json
import logging

import httpx
from smart_open import open

from . import header_dict, jsonschema

logger = logging.getLogger("vaccinespotter")


def fetch(state, geojson_file):
    """
    Fetch Vaccine Spotter state feed to raw_output_dir

    Use smart-open to write into cloud storage, if raw_output_dir is a gs:// url
    """

    url = f"https://www.vaccinespotter.org/api/v0/states/{state}.json"
    logger.info(f"Fetching {url}")

    with httpx.Client(headers=header_dict) as client:
        r = client.get(url)

    logger.info(f"Writing to {geojson_file}")
    with open(geojson_file, "w") as fh:
        fh.write(r.text)


def parse(geojson_file, ndjson_file):
    """
    Parse geojson_file into ndjson_file.

    Use smart-open to read from and write to GCS, if provided with gs:// urls
    """

    logger.info(f"Parsing {geojson_file}")
    with open(geojson_file) as fh:
        geojson = json.load(fh)

    logger.info(f"Writing {ndjson_file}")
    with open(ndjson_file, "w") as fh:
        for loc in geojson["features"]:
            json.dump(loc, fh)
            fh.write("\n")


def normalize(ndjson_file, normalized_ndjson_file):
    """ Convert ndjson_file into a normalized output file """

    logger.info(f"Normalizing {ndjson_file} to {normalized_ndjson_file}")
    with open(ndjson_file) as fin:
        with open(normalized_ndjson_file, "w") as fout:
            for line in fin:
                loc = json.loads(line)

                props = loc["properties"]
                long, lat = loc["geometry"]["coordinates"]

                location = jsonschema.Location(
                    id=f"vaccinespotter:{props['id']}",  # machinetag not hash
                    name=props["name"],
                    street1=props["address"],
                    city=props["city"],
                    state=props["state"],
                    zip=props["postal_code"],
                    latitude=lat,
                    longitude=long,
                    website=props["url"],
                    provider_id=f"{props['provider']}:{props['provider_location_id']}",
                    provider_name=props[
                        "provider_brand_name"
                    ],  # provider, provider_brand, or provider_brand_name?
                )

                d = jsonschema.to_dict(location)
                json.dump(d, fout)
                fout.write("\n")
