"""Pull futures prices from Yahoo Finance (no API key needed)."""
import httpx

FUTURES_MAP = {
    "corn": "ZC=F",
    "wheat": "ZW=F",
    "soybeans": "ZS=F",
    "corn_dec": "ZCZ26.CBT",
    "wheat_dec": "ZWZ26.CBT",
    "soybeans_dec": "ZSX26.CBT",
}


async def get_futures_prices(symbols: list[str] | None = None) -> str:
    """Fetch current futures prices. Symbols default to corn/wheat/soy."""
    if symbols is None:
        symbols = list(FUTURES_MAP.values())

    results = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for symbol in symbols:
            try:
                # Yahoo Finance v8 API (unofficial but reliable)
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
                params = {"range": "5d", "interval": "1d"}
                headers = {"User-Agent": "Mozilla/5.0"}
                resp = await client.get(url, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    meta = data.get("chart", {}).get("result", [{}])[0].get("meta", {})
                    price = meta.get("regularMarketPrice", "N/A")
                    prev = meta.get("previousClose", "N/A")
                    name = meta.get("shortName", symbol)
                    results.append(f"  {name} ({symbol}): ${price} (prev close: ${prev})")
                else:
                    results.append(f"  {symbol}: [HTTP {resp.status_code}]")
            except Exception as e:
                results.append(f"  {symbol}: [fetch failed: {e}]")

    return "Futures Prices (current):\n" + "\n".join(results) if results else "[No futures data]"
