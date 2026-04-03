# Project Memory

## Architecture
This repo contains **content-engine**, the Threeglau Content Agency.
It replaces the earlier `content-brief-gen` prototype.

## Key References
- **Sybil**: Global crops pricing system. Powers the `sibyl` domain in content-engine,
  pulling ENSO forecasts, USDA supply data, crop futures, and temperature thresholds.
- **Alpha Engine**: AI-powered options trading system. Domain: `alpha-engine`.
- **Argus**: Geopolitical risk and macro regime analysis. Domain: `argus`.

## Content Engine Layout
```
content-engine/
├── cli.py                       # CLI: `brief` and `signals` commands
├── src/
│   ├── config.py                # Env vars, model defaults
│   ├── signals/
│   │   ├── collector.py         # Standalone signal collection
│   │   └── sources/             # NOAA, USDA, Yahoo, crop temps, Grok web search
│   ├── editorial/
│   │   ├── style_guide.py       # Unified Threeglau style guide (essay DNA)
│   │   ├── prompts.py           # System + user prompt builders
│   │   ├── curator.py           # Domain routing + concurrent signal assembly
│   │   ├── writer.py            # LLM brief generation
│   │   └── pipeline.py          # Curator → Writer orchestrator
│   └── llm/
│       └── deepseek.py          # Shared DeepSeek R1/V3 client
```

## Style Guide
The essay style follows a 5-Act structure (Hook → Problem → Quantitative Pivot →
So What → Practical Path) with Point-Evidence-Soul argument blocks.
Full reference in `src/editorial/style_guide.py`.
