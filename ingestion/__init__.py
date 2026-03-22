"""VC Pulse data ingestion modules."""

# Keyword-to-sector mapping for normalizing sector tags
SECTOR_KEYWORDS: dict[str, str] = {
    # AI/ML
    "ai": "AI/ML", "artificial intelligence": "AI/ML", "machine learning": "AI/ML",
    "ml": "AI/ML", "llm": "AI/ML", "deep learning": "AI/ML", "nlp": "AI/ML",
    "generative ai": "AI/ML", "gen ai": "AI/ML", "gpt": "AI/ML", "chatbot": "AI/ML",
    "computer vision": "AI/ML", "neural": "AI/ML", "transformer": "AI/ML",
    # Fintech
    "fintech": "Fintech", "payments": "Fintech", "banking": "Fintech",
    "neobank": "Fintech", "defi": "Fintech", "lending": "Fintech",
    "insurance": "Fintech", "insurtech": "Fintech", "regtech": "Fintech",
    "wealth management": "Fintech", "credit": "Fintech",
    # Health
    "health": "HealthTech", "healthtech": "HealthTech", "biotech": "HealthTech",
    "medtech": "HealthTech", "pharma": "HealthTech", "clinical": "HealthTech",
    "telemedicine": "HealthTech", "genomics": "HealthTech", "drug discovery": "HealthTech",
    # CleanTech
    "climate": "CleanTech", "cleantech": "CleanTech", "energy": "CleanTech",
    "solar": "CleanTech", "battery": "CleanTech", "ev": "CleanTech",
    "sustainability": "CleanTech", "carbon": "CleanTech", "renewable": "CleanTech",
    "green": "CleanTech",
    # SaaS/Enterprise
    "saas": "SaaS/Enterprise", "enterprise": "SaaS/Enterprise", "b2b": "SaaS/Enterprise",
    "crm": "SaaS/Enterprise", "erp": "SaaS/Enterprise", "workflow": "SaaS/Enterprise",
    "productivity": "SaaS/Enterprise", "collaboration": "SaaS/Enterprise",
    # Crypto/Web3
    "crypto": "Crypto/Web3", "blockchain": "Crypto/Web3", "web3": "Crypto/Web3",
    "nft": "Crypto/Web3", "token": "Crypto/Web3", "dao": "Crypto/Web3",
    "ethereum": "Crypto/Web3", "bitcoin": "Crypto/Web3",
    # Security
    "cybersecurity": "Security", "security": "Security", "infosec": "Security",
    "zero trust": "Security", "identity": "Security", "auth": "Security",
    # DevTools
    "developer": "DevTools", "devtools": "DevTools", "devops": "DevTools",
    "infrastructure": "DevTools", "cloud": "DevTools", "kubernetes": "DevTools",
    "api": "DevTools", "open source": "DevTools", "database": "DevTools",
    # E-commerce/Consumer
    "ecommerce": "E-commerce", "e-commerce": "E-commerce", "retail": "E-commerce",
    "marketplace": "E-commerce", "d2c": "E-commerce", "consumer": "Consumer",
    # EdTech
    "education": "EdTech", "edtech": "EdTech", "learning": "EdTech",
    # Logistics
    "logistics": "Logistics", "supply chain": "Logistics", "shipping": "Logistics",
    "warehouse": "Logistics", "freight": "Logistics",
    # PropTech
    "real estate": "PropTech", "proptech": "PropTech", "housing": "PropTech",
    # Robotics
    "robotics": "Robotics", "autonomous": "Robotics", "drone": "Robotics",
    # Space
    "space": "SpaceTech", "satellite": "SpaceTech", "aerospace": "SpaceTech",
}


def classify_sector(text: str) -> str | None:
    """Classify text into a sector based on keyword matching."""
    if not text:
        return None
    text_lower = text.lower()
    sector_scores: dict[str, int] = {}
    for keyword, sector in SECTOR_KEYWORDS.items():
        if keyword in text_lower:
            sector_scores[sector] = sector_scores.get(sector, 0) + 1
    if not sector_scores:
        return None
    return max(sector_scores, key=sector_scores.get)


def parse_amount(text: str) -> float | None:
    """Extract dollar amount from text like '$50M', '$1.2B', '$500K'."""
    if not text:
        return None
    import re
    match = re.search(r"\$\s*([\d,.]+)\s*([BMKbmk](?:illion|illion)?)?", text)
    if not match:
        match = re.search(r"([\d,.]+)\s*(billion|million|thousand)", text, re.IGNORECASE)
        if not match:
            return None
    num_str = match.group(1).replace(",", "")
    try:
        num = float(num_str)
    except ValueError:
        return None
    multiplier_str = (match.group(2) or "").upper()
    if multiplier_str.startswith("B"):
        num *= 1_000_000_000
    elif multiplier_str.startswith("M"):
        num *= 1_000_000
    elif multiplier_str.startswith("K") or multiplier_str.startswith("T"):
        num *= 1_000
    return num


def parse_round_type(text: str) -> str | None:
    """Extract funding round type from text."""
    if not text:
        return None
    import re
    text_lower = text.lower()
    patterns = [
        (r"series\s+([a-h])\b", lambda m: f"series_{m.group(1)}"),
        (r"\b(seed)\b", lambda m: "seed"),
        (r"\b(pre-seed)\b", lambda m: "pre_seed"),
        (r"\b(ipo)\b", lambda m: "ipo"),
        (r"\b(spac)\b", lambda m: "spac"),
        (r"\b(growth)\b", lambda m: "growth"),
        (r"\b(bridge)\b", lambda m: "bridge"),
        (r"\b(debt)\b", lambda m: "debt"),
        (r"\b(grant)\b", lambda m: "grant"),
        (r"\b(angel)\b", lambda m: "angel"),
    ]
    for pattern, extractor in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return extractor(match)
    return None
