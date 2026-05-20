import requests
from bs4 import BeautifulSoup
import json
import time
import logging

from load_django import *
from parser_app.models import Category, Product

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

AVAILABILITY_MAP = {
    "https://schema.org/InStock": "InStock",
    "https://schema.org/LimitedAvailability": "LimitedAvailability",
}
ALLOWED_AVAILABILITY = set(AVAILABILITY_MAP.keys())


def get_all_allo_tv_data(base_url, category):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "uk-UA,uk;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    all_offers = []
    page = 1

    while True:
        if page == 1:
            url = base_url
        else:
            url = f"{base_url}p-{page}/"

        logger.info("Parsing page %d: %s", page, url)

        try:
            response = requests.get(url, headers=headers, allow_redirects=True)
            response.raise_for_status()

            if page > 1 and f"p-{page}" not in response.url:
                logger.warning("Reached the end of the catalog. Requested page %d, but server returned %s", page, response.url)
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            json_ld_scripts = soup.find_all('script', type='application/ld+json')

            page_has_products = False

            for script in json_ld_scripts:
                if script.string:
                    try:
                        data = json.loads(script.string)

                        if "@graph" in data:
                            for item in data["@graph"]:
                                if item.get("@type") == "Product" and "offers" in item:
                                    offers = item["offers"]
                                    logger.info("Found %d products on page %d.", len(offers), page)

                                    all_offers.extend(offers)
                                    page_has_products = True

                                    for offer in offers:
                                        product_url = offer.get("url")
                                        if not product_url:
                                            continue

                                        availability_url = offer.get("availability", "")
                                        if availability_url not in ALLOWED_AVAILABILITY:
                                            logger.warning(
                                                "Skipping out of stock product: %s", product_url
                                            )
                                            continue

                                        availability = AVAILABILITY_MAP[availability_url]
                                        product, created = Product.objects.get_or_create(
                                            url=product_url,
                                            defaults={
                                                "category": category,
                                                "status": "Pending",
                                                "site_name": "allo.ua",
                                                "availabily": availability,
                                                "brand": "",
                                                "name": "",
                                                "old_price": 0,
                                                "current_price": 0,
                                                "discount_percent": 0,
                                                "discount_amount": 0,
                                            }
                                        )
                                        if created:
                                            logger.info(
                                                "Added Pending [%s]: %s", availability, product_url
                                            )
                                        else:
                                            logger.info("Already exists: %s", product_url)

                                    break

                    except json.JSONDecodeError:
                        continue

                if page_has_products:
                    break


            if not page_has_products:
                logger.error("No JSON-LD product block found on page %d. The page structure may have changed.", page)
                break

            page += 1

            time.sleep(1)

        except requests.exceptions.RequestException as e:
            logger.error("Request failed: %s", e)
            break

    logger.info("Parsing completed. Total products collected: %d.", len(all_offers))

    return all_offers


categories = Category.objects.filter(link__isnull=False).exclude(link="")

for category in categories:
    logger.info("Processing category: %s (%s)", category.name, category.link)
    get_all_allo_tv_data(category.link, category)
    category.status = "Done"
    category.save()
    logger.info("Category '%s' marked as Done.", category.name)
