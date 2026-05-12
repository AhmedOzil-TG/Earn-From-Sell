import re
import logging
import httpx
import phonenumbers

logger = logging.getLogger(__name__)

import pycountry

# Comprehensive country mapping including common translations
COUNTRY_LOOKUP = {
    # Manual additions for common Arabic/Persian names
    "أمريكا": "US", "امريكا": "US", "الولايات المتحدة": "US", "ایالات متحده": "US",
    "كندا": "CA", "كانادا": "CA", "کانادا": "CA",
    "روسيا": "RU", "روسیه": "RU",
    "البرازيل": "BR", "برزیل": "BR",
    "ألمانيا": "DE", "آلمان": "DE",
    "البرتغال": "PT", "پرتغال": "PT",
    "فرنسا": "FR", "فرانسه": "FR",
    "بريطانيا": "GB", "انگلستان": "GB", "المملكة المتحدة": "GB",
    "إسبانيا": "ES", "اسپانیا": "ES",
    "إيطاليا": "IT", "ایتالیا": "IT",
    "تركيا": "TR", "ترکیه": "TR",
    "مصر": "EG",
    "السعودية": "SA", "عربستان": "SA",
    "الإمارات": "AE", "امارات": "AE",
    "العراق": "IQ",
    "قزاقستان": "KZ", "كازاخستان": "KZ",
}

# Auto-populate with English names from pycountry
for country in pycountry.countries:
    COUNTRY_LOOKUP[country.name.lower()] = country.alpha_2
    if hasattr(country, 'common_name'):
        COUNTRY_LOOKUP[country.common_name.lower()] = country.alpha_2
    if hasattr(country, 'official_name'):
        COUNTRY_LOOKUP[country.official_name.lower()] = country.alpha_2

def parse_price_message(text: str, pattern: str = None):
    results = []
    try:
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            
            # 1. Look for Country Name
            iso_code = None
            # Check manual/common names first for performance and specificity
            for name, code in COUNTRY_LOOKUP.items():
                if name.lower() in line_lower:
                    iso_code = code
                    break
            
            # 2. Look for Phone Prefix (e.g. +1, +44)
            prefix_matches = re.findall(r'\+(\d{1,4})\b', line)
            if prefix_matches:
                prefix = int(prefix_matches[0])
                # If we haven't found a code by name yet, use the prefix
                if not iso_code:
                    iso_code = phonenumbers.region_code_for_country_code(prefix)
            
            # 3. Look for Price
            price_matches = re.findall(r'(?:(\d+\.\d+|\d+)\s*\$|\$\s*(\d+\.\d+|\d+))', line)
            
            if iso_code and iso_code != "ZZ" and price_matches:
                p1, p2 = price_matches[0]
                sell_price = float(p1 or p2)
                results.append((iso_code, sell_price))
                    
        # Fallback for single-country messages where components are on different lines
        if not results:
            text_lower = text.lower()
            iso_code = None
            for name, code in COUNTRY_LOOKUP.items():
                if name.lower() in text_lower:
                    iso_code = code
                    break
            
            prefix_matches = re.findall(r'\+(\d{1,4})\b', text)
            if prefix_matches and not iso_code:
                iso_code = phonenumbers.region_code_for_country_code(int(prefix_matches[0]))
            
            price_matches = re.findall(r'(?:(\d+\.\d+|\d+)\s*\$|\$\s*(\d+\.\d+|\d+))', text)
            if iso_code and iso_code != "ZZ" and price_matches:
                p1, p2 = price_matches[0]
                sell_price = float(p1 or p2)
                results.append((iso_code, sell_price))
                    
    except Exception as e:
        logger.error(f"Error parsing message: {e}")
    
    return results

async def fetch_buy_prices_api(server_urls: list):
    aggregated_prices = {}
    async with httpx.AsyncClient() as client:
        for url in server_urls:
            try:
                response = await client.get(url)
                data = response.json()
                if data.get("ok") and isinstance(data.get("result"), dict):
                    result = data["result"]
                    countries_container = result.get("countries", {})
                    if isinstance(countries_container, dict):
                        # The pattern usually is result -> countries -> '1'
                        countries_data = countries_container.get("1", {})
                        if isinstance(countries_data, dict):
                            for k, v in countries_data.items():
                                try:
                                    price = float(v)
                                    if k not in aggregated_prices:
                                        aggregated_prices[k] = []
                                    aggregated_prices[k].append({"price": price, "server": url})
                                except (ValueError, TypeError):
                                    continue
            except Exception as e:
                logger.error(f"Error fetching from {url}: {e}")
    
    # Sort lists so cheapest is first
    for k in aggregated_prices:
        aggregated_prices[k].sort(key=lambda x: x["price"])
    return aggregated_prices
