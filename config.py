"""Central configuration: model registry, paths, spend ceiling, and API keys loaded from environment."""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

CONFIG = {
    "models": [
        {
            "provider": "anthropic",
            "api_id": "claude-sonnet-5",
            "price_per_million_in": 3.00,
            "price_per_million_out": 15.00,
            "rpm_limit": 50,
            "daily_request_cap": 1000,
        },
        {
            "provider": "openai",
            "api_id": "gpt-5",
            "price_per_million_in": 5.00,
            "price_per_million_out": 15.00,
            "rpm_limit": 50,
            "daily_request_cap": 1000,
        },
        {
            "provider": "deepseek",
            "api_id": "deepseek-chat",
            "price_per_million_in": 0.27,
            "price_per_million_out": 1.10,
            "rpm_limit": 50,
            "daily_request_cap": 1000,
        },
        {
            "provider": "together",
            "api_id": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "price_per_million_in": 0.88,
            "price_per_million_out": 0.88,
            "rpm_limit": 50,
            "daily_request_cap": 1000,
        },
        {
            "provider": "google",
            "api_id": "gemini-2.5-pro",
            "price_per_million_in": 1.25,
            "price_per_million_out": 10.00,
            "rpm_limit": 50,
            "daily_request_cap": 1000,
        },
    ],
    "paths": {
        "items_file": ROOT_DIR / "items" / "items.yaml",
        "prompts_dir": ROOT_DIR / "items" / "prompts",
        "raw_dir": ROOT_DIR / "data" / "raw",
        "parsed_dir": ROOT_DIR / "data" / "parsed",
        "figures_dir": ROOT_DIR / "report" / "figures",
    },
    "total_spend_ceiling_usd": 50.00,
    "api_keys": {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
        "openai": os.environ.get("OPENAI_API_KEY"),
        "deepseek": os.environ.get("DEEPSEEK_API_KEY"),
        "together": os.environ.get("TOGETHER_API_KEY"),
        "google": os.environ.get("GOOGLE_API_KEY"),
    },
}
