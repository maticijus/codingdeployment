"""Pull USDA supply/demand context via NASS Quick Stats API."""
import httpx


async def get_usda_context(commodity: str = "corn") -> str:
    """Get basic USDA supply context. Commodity = corn, wheat, soybeans."""
    context_parts = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            params = {
                "source_desc": "SURVEY",
                "commodity_desc": commodity.upper(),
                "statisticcat_desc": "AREA PLANTED",
                "unit_desc": "ACRES",
                "agg_level_desc": "NATIONAL",
                "year__GE": "2023",
                "format": "JSON",
            }
            resp = await client.get(
                "https://quickstats.nass.usda.gov/api/api_GET/",
                params={"key": "DEMO_KEY", **params}
            )
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                if data:
                    recent = sorted(data, key=lambda x: x.get("year", ""), reverse=True)[:3]
                    lines = [f"  {r['year']}: {r.get('Value', 'N/A')} acres" for r in recent]
                    context_parts.append(f"USDA {commodity.title()} Planted Acres (recent):\n" + "\n".join(lines))
        except Exception as e:
            context_parts.append(f"[USDA acres fetch failed: {e}]")

    return "\n\n".join(context_parts) if context_parts else f"[No USDA data for {commodity}]"
