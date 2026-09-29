"""
Configuration and domain definitions for Stock Market Analyzer.
Covers AI, Chips (Semiconductors), and Energy domains.
"""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "analyzer.db"

# Tracked stock universe categorized by domain
DOMAINS = {
    "AI": {
        "name": "Artificial Intelligence",
        "description": "Enterprise AI software, LLM foundation models, cloud infrastructure & automation",
        "queries": [
            "AI stocks when:7d",
            "artificial intelligence stock news when:7d",
            "enterprise AI market software when:7d"
        ],
        "stocks": {
            "NVDA": {"name": "Nvidia Corporation", "role": "AI compute & GPU architecture leader"},
            "MSFT": {"name": "Microsoft Corporation", "role": "Enterprise AI & cloud copilot integration"},
            "GOOGL": {"name": "Alphabet Inc.", "role": "Gemini AI models & cloud AI platform"},
            "META": {"name": "Meta Platforms", "role": "Open source AI models (Llama) & AI infra"},
            "AMZN": {"name": "Amazon.com Inc.", "role": "AWS cloud AI infrastructure & Bedrock"},
            "PLTR": {"name": "Palantir Technologies", "role": "AI enterprise platforms (AIP) & defense"},
            "ORCL": {"name": "Oracle Corporation", "role": "Cloud AI data centers & OCI expansion"},
            "CRM": {"name": "Salesforce Inc.", "role": "Agentforce enterprise AI agents"},
            "IBM": {"name": "IBM Corporation", "role": "Enterprise Watsonx generative AI"},
            "AAPL": {"name": "Apple Inc.", "role": "Apple Intelligence edge AI consumer ecosystem"},
            "AI": {"name": "C3.ai Inc.", "role": "Enterprise AI application software"},
            "TSLA": {"name": "Tesla Inc.", "role": "Autonomous Full Self-Driving AI, Dojo supercomputer & Megapack grid storage"},
            "PATH": {"name": "UiPath Inc.", "role": "Agentic process automation & AI workflows"},
            "NOW": {"name": "ServiceNow Inc.", "role": "Workflow automation & enterprise GenAI"},
            "SNOW": {"name": "Snowflake Inc.", "role": "AI data cloud & enterprise analytics"}
        }
    },
    "Chips": {
        "name": "Semiconductors & Hardware",
        "description": "Foundries, chip designers, semiconductor lithography, memory & fab equipment",
        "queries": [
            "semiconductor stocks when:7d",
            "chip stocks market earnings when:7d",
            "chipmaker demand semiconductor export when:7d"
        ],
        "stocks": {
            "TSM": {"name": "Taiwan Semiconductor (TSMC)", "role": "Leading advanced node semiconductor foundry"},
            "AMD": {"name": "Advanced Micro Devices", "role": "MI300 AI accelerators & server CPUs"},
            "AVGO": {"name": "Broadcom Inc.", "role": "Custom AI ASICs & networking silicon"},
            "ASML": {"name": "ASML Holding", "role": "EUV photolithography semiconductor equipment monopoly"},
            "QCOM": {"name": "Qualcomm Inc.", "role": "Snapdragon edge AI & mobile/automotive processors"},
            "INTC": {"name": "Intel Corporation", "role": "x86 CPUs, foundry spin-off restructuring"},
            "MU": {"name": "Micron Technology", "role": "High Bandwidth Memory (HBM3e) for AI servers"},
            "ARM": {"name": "Arm Holdings", "role": "Energy-efficient compute architecture licensing"},
            "MRVL": {"name": "Marvell Technology", "role": "Custom AI electro-optics & data center silicon"},
            "TXN": {"name": "Texas Instruments", "role": "Analog chips & industrial/automotive silicon"},
            "AMAT": {"name": "Applied Materials", "role": "Semiconductor manufacturing equipment"},
            "LRCX": {"name": "Lam Research", "role": "Wafer fabrication etch & deposition equipment"},
            "KLAC": {"name": "KLA Corporation", "role": "Process control & yield management tools"},
            "SMCI": {"name": "Super Micro Computer", "role": "AI server liquid cooling & GPU cluster racks"}
        }
    },
    "Energy": {
        "name": "Energy & Power for AI",
        "description": "Nuclear/SMR power for data centers, utilities, clean renewables, and grid infrastructure",
        "queries": [
            "energy stocks AI power data center when:7d",
            "nuclear energy stocks AI electricity demand when:7d",
            "clean energy utility stocks when:7d",
            "oil gas energy market when:7d"
        ],
        "stocks": {
            "VST": {"name": "Vistra Corp", "role": "Merchant power producer & nuclear generation for AI"},
            "CEG": {"name": "Constellation Energy", "role": "Clean nuclear power contracts for data centers"},
            "CCJ": {"name": "Cameco Corporation", "role": "Uranium fuel supply for nuclear energy reactors"},
            "OKLO": {"name": "Oklo Inc.", "role": "Small modular nuclear reactors (SMR) for clean power"},
            "SMR": {"name": "NuScale Power", "role": "SMR nuclear technology developer"},
            "GEV": {"name": "GE Vernova", "role": "Power generation turbines & electrical grid equipment"},
            "NEE": {"name": "NextEra Energy", "role": "Largest renewable utility & clean energy developer"},
            "NRG": {"name": "NRG Energy", "role": "Independent power producer & retail energy services"},
            "XOM": {"name": "ExxonMobil", "role": "Integrated oil & gas major, carbon capture ventures"},
            "CVX": {"name": "Chevron Corporation", "role": "Global energy exploration, LNG & refining"},
            "FSLR": {"name": "First Solar Inc.", "role": "Domestic thin-film solar PV module manufacturer"},
            "ENPH": {"name": "Enphase Energy", "role": "Solar microinverters & residential battery storage"},
            "OXY": {"name": "Occidental Petroleum", "role": "Permian Basin shale oil & direct air carbon capture"},
            "SEDG": {"name": "SolarEdge Technologies", "role": "Solar smart energy hardware & optimizers"}
        }
    }
}

# Positive sentiment keywords and market catalyst terms
POSITIVE_KEYWORDS = [
    "beat", "beats", "record", "surge", "surges", "surging", "soar", "soars", "rally", "rallies",
    "upgrade", "upgrades", "upgraded", "buy", "outperform", "bull", "bullish", "growth",
    "profit", "strong", "higher", "gain", "gains", "partnership", "contract", "deal", "breakthrough",
    "expansion", "accelerat", "demand", "ai boom", "dividend", "revenue up", "top pick", "raise"
]

# Negative sentiment keywords and risk/headwind terms
NEGATIVE_KEYWORDS = [
    "drop", "drops", "dropping", "fall", "falls", "falling", "slump", "slumps", "plunge", "plunges",
    "tumble", "tumbles", "slide", "slides", "downgrade", "downgrades", "sell", "underperform",
    "bear", "bearish", "loss", "losses", "cut", "cuts", "probe", "investigat", "antitrust",
    "lawsuit", "delay", "delayed", "restriction", "restrictions", "tariff", "tariffs", "ban",
    "warning", "warns", "caution", "weak", "miss", "misses", "pullback", "retreat", "retreats",
    "margin pressure", "debt", "risk", "risks", "headwind", "headwinds"
]
