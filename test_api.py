import asyncio
import httpx
import json

async def f():
    res = await httpx.AsyncClient().get('https://www.max-tg.com/sub/api/?apiKay=syi3tvulvjgp1clefn4x&action=getCountrys')
    data = res.json()['result']['countries']['1']
    print("Is IN in data?", "IN" in data)
    print("Is India in data?", "India" in data)
    for key, value in data.items():
        if "IN" in key or "in" in key.lower():
            print(f"Found something with IN: {key}: {value}")
            
    with open('api_dump.json', 'w') as f2:
        json.dump(data, f2, indent=2)

asyncio.run(f())
