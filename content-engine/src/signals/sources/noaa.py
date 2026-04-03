"""Pull current ENSO state and forecast from NOAA CPC."""
import re
import httpx

ENSO_STATUS_URL = "https://www.cpc.ncep.noaa.gov/products/analysis_monitoring/enso_advisory/ensodisc.shtml"
ENSO_DATA_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"


async def get_enso_context() -> str:
    """Fetch current ENSO advisory text and recent ONI values."""
    context_parts = []

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(ENSO_STATUS_URL)
            if resp.status_code == 200:
                text = resp.text
                pre_match = re.search(r'<[Pp][Rr][Ee]>(.*?)</[Pp][Rr][Ee]>', text, re.DOTALL)
                if pre_match:
                    advisory = pre_match.group(1).strip()[:3000]
                    context_parts.append(f"NOAA CPC ENSO Advisory (current):\n{advisory}")
        except Exception as e:
            context_parts.append(f"[ENSO advisory fetch failed: {e}]")

        try:
            resp = await client.get(ENSO_DATA_URL)
            if resp.status_code == 200:
                lines = resp.text.strip().split("\n")
                recent = lines[-6:]
                context_parts.append(f"Recent ONI values (last 6 quarters):\n" + "\n".join(recent))
        except Exception as e:
            context_parts.append(f"[ONI data fetch failed: {e}]")

    return "\n\n".join(context_parts) if context_parts else "[No ENSO data available]"
