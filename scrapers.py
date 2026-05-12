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

# Mapping of keywords to ISO codes for disambiguation
COUNTRY_KEYWORDS = {
    "US": ["usa", "united states", "أمريكا", "امريكا", "ایالات متحده"],
    "CA": ["canada", "كانادا", "کانادا"],
    "RU": ["russia", "روسیه", "روسيا"],
    "KZ": ["kazakhstan", "قزاقستان", "كازاخستان"],
    "PR": ["puerto rico", "بورتوريكو"],
    "DO": ["dominican", "الدومينيكان"],
}

def parse_price_message(text: str, pattern: str = None):
    results = []
    try:
        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower()
            prefix_matches = re.findall(r'\+(\d{1,4})\b', line)
            price_matches = re.findall(r'(?:(\d+\.\d+|\d+)\s*\$|\$\s*(\d+\.\d+|\d+))', line)
            
            if prefix_matches and price_matches:
                prefix = int(prefix_matches[0])
                # Find default region code
                code = phonenumbers.region_code_for_country_code(prefix)
                
                # Check for other regions with same prefix (like Canada for +1)
                all_regions = phonenumbers.country_code_to_region_code.get(prefix, ())
                if len(all_regions) > 1:
                    for region in all_regions:
                        keywords = COUNTRY_KEYWORDS.get(region, [])
                        if any(kw in line_lower for kw in keywords):
                            code = region
                            break
                
                price_str = price_matches[0][0] or price_matches[0][1]
                sell_price = float(price_str)
                
                if code and code != "ZZ":
                    results.append((code, sell_price))
                    
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
