import re
import logging
import httpx
import phonenumbers

logger = logging.getLogger(__name__)

# Mapping Persian/Arabic country names to ISO codes (as fallback)
COUNTRY_MAP = {
    "لیتوانی": "LT",
    "عربستان": "SA",
    "روسیه": "RU",
    "برزیل": "BR",
    "آلمان": "DE",
}

def parse_price_message(text: str, pattern: str = None):
    """
    Universally parses a message and returns a list of (iso_code, price) tuples.
    It ignores the 'pattern' parameter and uses a heuristic to find country phone
    prefixes and USD prices in the message.
    """
    results = []
    try:
        # First, try to process line by line (or sentence by sentence)
        # This handles lists of countries nicely
        lines = text.split('\n')
        for line in lines:
            prefix_matches = re.findall(r'\+(\d{1,4})\b', line)
            price_matches = re.findall(r'(?:(\d+\.\d+|\d+)\s*\$|\$\s*(\d+\.\d+|\d+))', line)
            
            if prefix_matches and price_matches:
                # Pair the first prefix with the first price on this line
                prefix = int(prefix_matches[0])
                price_str = price_matches[0][0] or price_matches[0][1]
                sell_price = float(price_str)
                
                code = phonenumbers.region_code_for_country_code(prefix)
                if code and code != "ZZ":
                    results.append((code, sell_price))
                    
        # If no results found line-by-line, maybe the prefix and price are on different lines 
        # but the whole message is about ONE country.
        if not results:
            prefix_matches = re.findall(r'\+(\d{1,4})\b', text)
            price_matches = re.findall(r'(?:(\d+\.\d+|\d+)\s*\$|\$\s*(\d+\.\d+|\d+))', text)
            
            # Match the first prefix with the first price found in the message
            if prefix_matches and price_matches:
                prefix = int(prefix_matches[0])
                price_str = price_matches[0][0] or price_matches[0][1]
                sell_price = float(price_str)
                
                code = phonenumbers.region_code_for_country_code(prefix)
                if code and code != "ZZ":
                    results.append((code, sell_price))
                    
    except Exception as e:
        logger.error(f"Error universally parsing: {e}")
    
    return results

async def fetch_buy_prices_api(server_urls: list):
    aggregated_prices = {}
    async with httpx.AsyncClient() as client:
        for url in server_urls:
            try:
                response = await client.get(url)
                data = response.json()
                if data.get("ok"):
                    # Assuming the structure is result -> countries -> '1' (common pattern)
                    countries_data = data["result"]["countries"]["1"]
                    for k, v in countries_data.items():
                        # Update if not present or found better price (lower buy price is better)
                        if k not in aggregated_prices or float(v) < aggregated_prices[k]:
                            aggregated_prices[k] = float(v)
            except Exception as e:
                logger.error(f"Error fetching from {url}: {e}")
    return aggregated_prices
