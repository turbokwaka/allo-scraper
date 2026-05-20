import requests
from bs4 import BeautifulSoup
import re
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed


from load_django import *
from parser_app.models import Product

MAX_WORKERS = 5

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_full_allo_product(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "uk-UA,uk;q=0.9"
    }

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        allo_script = None
        for script in soup.find_all('script'):
            if script.string and 'window.__ALLO__' in script.string:
                allo_script = script.string
                break

        if not allo_script:
            return None

        cat_path_match = re.search(r'categories_path:"([^"]+)"', allo_script)
        if cat_path_match:
            raw_path = cat_path_match.group(1)
            path_parts = re.split(r'\s*(?:>|\\u003E)\s*', raw_path)

            category = path_parts[1] if len(path_parts) > 1 else None
            name = path_parts[-1]
            if len(path_parts) > 2:
                brand = path_parts[2].replace(category, "").strip()
            else:
                brand = None
        else:
            category, name, brand = None, None, None

        current_price = 0.0
        all_possible_prices = []
        is_in_stock = True

        json_ld_scripts = soup.find_all('script', type='application/ld+json')
        for script in json_ld_scripts:
            if script.string and '"@type":"Product"' in script.string:
                try:
                    data = json.loads(script.string)
                    if "@graph" in data:
                        for item in data["@graph"]:
                            if item.get("@type") == "Product" and "offers" in item:
                                offers = item["offers"]
                                if isinstance(offers, dict):
                                    current_price = float(offers.get("price", 0))
                                    if "OutOfStock" in offers.get("availability", ""):
                                        is_in_stock = False
                                elif isinstance(offers, list) and len(offers) > 0:
                                    current_price = float(offers[0].get("price", 0))
                                    if "OutOfStock" in offers[0].get("availability", ""):
                                        is_in_stock = False
                except json.JSONDecodeError:
                    pass

        if not current_price:
            cur_price_elem = soup.select_one('.v-pb__cur .sum, .price-box__cur, .current-price, [itemprop="price"]')
            if cur_price_elem:
                if cur_price_elem.has_attr('content'):
                    current_price = float(cur_price_elem['content'])
                else:
                    digits = re.sub(r'[^\d]', '', cur_price_elem.get_text())
                    if digits:
                        current_price = float(digits)

        all_possible_prices.append(current_price)

        if is_in_stock:
            buy_block = soup.select_one('.p-trade, .buy-box, .product-main-info')
            if buy_block and 'немає в наявності' in buy_block.get_text(strip=True).lower():
                is_in_stock = False

        price_matches = re.findall(
            r'(?:price|special_price|old_price|base_price|regular_price|magento_price)["\'\s:]*(\d{3,6})(?:[,}\s]|\.00)',
            allo_script, re.IGNORECASE)
        for p in price_matches:
            all_possible_prices.append(float(p))

        old_price_elems = soup.select(
            '.v-pb__old, .price-box__old, del, s, strike, [class*="old-price"], [class*="old_price"], .discount-price')
        for elem in old_price_elems:
            digits = re.sub(r'[^\d]', '', elem.get_text())
            if digits:
                all_possible_prices.append(float(digits))

        valid_old_prices = [p for p in all_possible_prices if current_price <= p <= (current_price * 10)]
        old_price = max(valid_old_prices) if valid_old_prices else current_price

        discount_sum = old_price - current_price
        discount_percent = round((discount_sum / old_price) * 100, 2) if old_price > 0 else 0

        if not is_in_stock:
            logger.warning("Product identified as OUT_OF_STOCK: %s", url)

        additional_info = {
            "images": [],
            "rating": 0.0,
            "reviews_count": 0,
            "sku": "",
            "specs": {}
        }

        for script in json_ld_scripts:
            if script.string and '"@type":"Product"' in script.string:
                try:
                    data = json.loads(script.string)
                    if "@graph" in data:
                        for item in data["@graph"]:
                            if item.get("@type") == "Product":
                                additional_info["sku"] = item.get("sku", "")
                                additional_info["images"] = item.get("image", [])

                                rating_data = item.get("aggregateRating", {})
                                additional_info["rating"] = float(rating_data.get("ratingValue", 0.0))
                                additional_info["reviews_count"] = int(rating_data.get("reviewCount", 0))
                                break
                except json.JSONDecodeError:
                    pass

        spec_rows = soup.select('.specs-property, .product-property, [class*="specs__item"]')

        for row in spec_rows:
            name_elem = row.select_one('[class*="name"], [class*="title"], dt')
            value_elem = row.select_one('[class*="value"], dd')

            if name_elem and value_elem:
                spec_name = name_elem.get_text(strip=True)
                spec_value = value_elem.get_text(separator=", ", strip=True)

                if spec_name and spec_value:
                    additional_info["specs"][spec_name] = spec_value

        if not additional_info["specs"]:
            for tr in soup.select('tr'):
                tds = tr.select('th, td')
                if len(tds) >= 2:
                    spec_name = tds[0].get_text(strip=True)
                    spec_value = tds[1].get_text(separator=", ", strip=True)
                    if spec_name and spec_value:
                        additional_info["specs"][spec_name] = spec_value

        db_record = {
            "site_name": "allo.ua",
            "category": category,
            "brand": brand,
            "old_price": int(old_price),
            "current_price": int(current_price) if is_in_stock else int(old_price),
            "discount_percent": discount_percent,
            "discount_amount": int(discount_sum),
            "name": name,
            "url": url,
            "is_in_stock": is_in_stock,
            "additional_info": additional_info
        }

        return db_record

    except Exception as e:
        logger.error("Failed to parse %s: %s", url, e)
        return None


def process_product(product_id):
    product = Product.objects.get(id=product_id)
    try:
        db_record = parse_full_allo_product(product.url)

        if db_record and not db_record.get("is_in_stock"):
            product.delete()
            logger.warning("Deleted out of stock product: %s", product.url)
        elif db_record:
            product.site_name = db_record["site_name"]
            product.brand = db_record["brand"]
            product.name = db_record["name"]
            product.sku = db_record["additional_info"].get("sku", "")
            product.old_price = db_record["old_price"]
            product.current_price = db_record["current_price"]
            product.discount_percent = db_record["discount_percent"]
            product.discount_amount = db_record["discount_amount"]
            product.additional_info = db_record["additional_info"]
            product.status = "Processed"
            product.save()
            logger.info("Processed: %s %s", product.brand, product.name)
        else:
            product.status = "Error"
            product.save()
            logger.warning("No data found for: %s", product.url)

    except Exception as e:
        product.status = "Error"
        product.save()
        logger.error("Error processing %s: %s", product.url, e)


pending_ids = list(Product.objects.filter(status__in=["Pending", "Error"]).values_list("id", flat=True))
total = len(pending_ids)
logger.info("Found %d products with status Pending or Error.", total)

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(process_product, pid): pid for pid in pending_ids}
    for i, future in enumerate(as_completed(futures), start=1):
        future.result()
        logger.info("Progress: %d/%d", i, total)

logger.info("Done. Processed %d products.", total)
