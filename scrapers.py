import re
import logging
import httpx
import phonenumbers

logger = logging.getLogger(__name__)

import os
import json
from deep_translator import GoogleTranslator
import pycountry

# Path for persistent translation cache
CACHE_PATH = "data/country_cache.json"

def load_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return {}
    return {}

def save_cache(cache):
    os.makedirs("data", exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

TRANSLATION_CACHE = load_cache()

def get_iso_from_name(name: str):
    name = name.strip().lower()
    if not name or len(name) < 2: return None
    
    # 1. Check local cache
    if name in TRANSLATION_CACHE:
        return TRANSLATION_CACHE[name]
    
    # 2. Try direct match with pycountry (English)
    try:
        match = pycountry.countries.search_fuzzy(name)
        if match:
            code = match[0].alpha_2
            TRANSLATION_CACHE[name] = code
            save_cache(TRANSLATION_CACHE)
            return code
    except: pass
    
    # 3. Translate to English using Google
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(name)
        match = pycountry.countries.search_fuzzy(translated)
        if match:
            code = match[0].alpha_2
            TRANSLATION_CACHE[name] = code # Cache the ORIGINAL name
            save_cache(TRANSLATION_CACHE)
            return code
    except Exception as e:
        logger.error(f"Translation error for {name}: {e}")
        
    return None

def parse_price_message(text: str, pattern: str = None):
    results = []
    try:
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Find price
            price_matches = re.findall(r'(?:(\d+\.\d+|\d+)\s*\$|\$\s*(\d+\.\d+|\d+))', line)
            if not price_matches: continue
            
            p1, p2 = price_matches[0]
            sell_price = float(p1 or p2)
            
            # Extract country candidate: strip price, prefix, and symbols
            candidate = line
            candidate = re.sub(r'(?:\d+\.\d+|\d+)\s*\$|\$\s*(\d+\.\d+|\d+)', '', candidate)
            prefix_matches = re.findall(r'\+(\d{1,4})\b', candidate)
            candidate = re.sub(r'\+\d{1,4}\b', '', candidate)
            candidate = re.sub(r'[^\w\s]', '', candidate) # Remove emojis/symbols
            candidate = candidate.strip()
            
            iso_code = get_iso_from_name(candidate)
            
            # Fallback to prefix if name failed
            if not iso_code and prefix_matches:
                prefix = int(prefix_matches[0])
                iso_code = phonenumbers.region_code_for_country_code(prefix)
            
            if iso_code and iso_code != "ZZ":
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
