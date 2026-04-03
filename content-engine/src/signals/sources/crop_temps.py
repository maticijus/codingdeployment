"""Crop temperature thresholds and stress analysis for Sybil."""
import re
import httpx

# Critical temperature thresholds (deg C) for major crops at key growth stages
CROP_TEMP_THRESHOLDS = {
    "corn": {
        "optimal_range": (25, 33),
        "stress_floor": 10,
        "stress_ceiling": 35,
        "kill_frost": -2,
        "stages": {
            "germination": {"optimal": (10, 30), "min": 10},
            "vegetative": {"optimal": (25, 33), "min": 15},
            "pollination": {"optimal": (25, 29), "max": 35},
            "grain_fill": {"optimal": (20, 28), "max": 35},
        },
    },
    "wheat": {
        "optimal_range": (15, 25),
        "stress_floor": 4,
        "stress_ceiling": 32,
        "kill_frost": -10,
        "stages": {
            "germination": {"optimal": (12, 25), "min": 4},
            "tillering": {"optimal": (10, 20), "min": 3},
            "heading": {"optimal": (15, 20), "max": 32},
            "grain_fill": {"optimal": (15, 25), "max": 30},
        },
    },
    "soybeans": {
        "optimal_range": (25, 30),
        "stress_floor": 10,
        "stress_ceiling": 36,
        "kill_frost": -2,
        "stages": {
            "germination": {"optimal": (15, 30), "min": 10},
            "vegetative": {"optimal": (25, 30), "min": 15},
            "flowering": {"optimal": (25, 30), "max": 36},
            "pod_fill": {"optimal": (22, 28), "max": 33},
        },
    },
}

TEMP_DISCUSSION_URL = "https://www.cpc.ncep.noaa.gov/products/predictions/long_range/fxus05.html"


def get_thresholds(commodity: str) -> str:
    """Return formatted crop temperature thresholds for a commodity."""
    commodity = commodity.lower()
    if commodity not in CROP_TEMP_THRESHOLDS:
        return f"[No temperature thresholds for {commodity}]"

    t = CROP_TEMP_THRESHOLDS[commodity]
    lines = [
        f"Crop Temperature Thresholds — {commodity.title()}:",
        f"  Optimal range: {t['optimal_range'][0]}–{t['optimal_range'][1]}°C",
        f"  Stress floor: {t['stress_floor']}°C | Stress ceiling: {t['stress_ceiling']}°C",
        f"  Kill frost: {t['kill_frost']}°C",
        f"  Growth stages:",
    ]
    for stage, params in t["stages"].items():
        opt = params["optimal"]
        bounds = []
        if "min" in params:
            bounds.append(f"min {params['min']}°C")
        if "max" in params:
            bounds.append(f"max {params['max']}°C")
        lines.append(f"    {stage}: optimal {opt[0]}–{opt[1]}°C ({', '.join(bounds)})")

    return "\n".join(lines)


async def get_temp_outlook_context() -> str:
    """Fetch CPC temperature outlook discussion for US crop belt."""
    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(TEMP_DISCUSSION_URL)
            if resp.status_code == 200:
                pre_match = re.search(r'<[Pp][Rr][Ee]>(.*?)</[Pp][Rr][Ee]>', resp.text, re.DOTALL)
                if pre_match:
                    text = pre_match.group(1).strip()[:3000]
                    return f"CPC Temperature Outlook Discussion:\n{text}"
                return "[Temperature outlook: could not parse discussion]"
            return f"[Temperature outlook fetch: HTTP {resp.status_code}]"
        except Exception as e:
            return f"[Temperature outlook fetch failed: {e}]"


async def get_crop_temp_context() -> str:
    """Get combined temperature thresholds + outlook for all Sybil crops."""
    parts = [
        get_thresholds("corn"),
        get_thresholds("wheat"),
        get_thresholds("soybeans"),
        "",
        await get_temp_outlook_context(),
    ]
    return "\n\n".join(parts)
