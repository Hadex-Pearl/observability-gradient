"""Central configuration: model registry, paths, spend ceiling, and API keys loaded from environment."""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent

CONFIG = {
    # "name" is the identifier written to log rows (row["model"]); "api_id" is
    # the exact string sent to the provider API. They can diverge if a
    # provider versions its api_id oddly.
    "models": [
        {
            "name": "claude-sonnet-5",
            "provider": "anthropic",
            "api_id": "claude-sonnet-5",
            "price_per_million_in": 3.00,
            "price_per_million_out": 15.00,
            "rpm_limit": 50,
            "daily_request_cap": 1000,
        },
        {
            "name": "gpt-5",
            "provider": "openai",
            "api_id": "gpt-5",
            "price_per_million_in": 5.00,
            "price_per_million_out": 15.00,
            "rpm_limit": 50,
            "daily_request_cap": 1000,
        },
        {
            "name": "deepseek-chat",
            "provider": "deepseek",
            "api_id": "deepseek-chat",
            "price_per_million_in": 0.27,
            "price_per_million_out": 1.10,
            "rpm_limit": 50,
            "daily_request_cap": 1000,
        },
        {
            "name": "llama-3.3-70b",
            "provider": "together",
            "api_id": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
            "price_per_million_in": 0.88,
            "price_per_million_out": 0.88,
            "rpm_limit": 50,
            "daily_request_cap": 1000,
        },
        {
            # Free-tier limits: ~15 RPM and a 1,500 requests/day cap.
            "name": "gemini-2.5-pro",
            "provider": "google",
            "api_id": "gemini-2.5-pro",
            "price_per_million_in": 1.25,
            "price_per_million_out": 10.00,
            "rpm_limit": 15,
            "daily_request_cap": 1500,
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

    # Per-level output cap, sent as the API max_tokens parameter (never as a
    # prompt instruction — models routinely ignore written brevity requests).
    # Level 2 is a forced-choice level with no room for reasoning-out-loud in
    # the visible text, hence the small cap; level 0 is the freest condition
    # and gets the most room so genuine in-progress answers aren't cut off
    # before they start (see calibration output in verify_log.py).
    "max_tokens_by_level": {
        3: 400,
        2: 32,
        1: 500,
        0: 800,
    },

    # Fixed for every condition. At temperature 0 all repeated runs in a cell
    # return the same response, which collapses the effective sample size to
    # 1 — never set this to 0 anywhere in the run path (enforced by the
    # assertion below and again in src/runner.py).
    "temperature": 1.0,

    # Reasoning/extended-thinking is disabled everywhere so token spend and
    # output are comparable across providers. Each adapter enforces this by
    # its own mechanism (see src/providers/*); this flag is what gets
    # recorded per row and passed to adapters.
    "reasoning_enabled": False,

    "backoff": {
        "base_seconds": 1.0,
        "max_seconds": 60.0,
        "max_retries": 5,
    },
    "api_keys": {
        "anthropic": os.environ.get("ANTHROPIC_API_KEY"),
        "openai": os.environ.get("OPENAI_API_KEY"),
        "deepseek": os.environ.get("DEEPSEEK_API_KEY"),
        "together": os.environ.get("TOGETHER_API_KEY"),
        "google": os.environ.get("GOOGLE_API_KEY"),
    },
}

assert CONFIG["temperature"] != 0, "temperature must never be 0 — it collapses repeated runs in a cell to n=1"


def models_by_name():
    """Model registry keyed by row["model"] name instead of list order."""
    return {m["name"]: m for m in CONFIG["models"]}
