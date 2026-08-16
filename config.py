"""Central configuration: model registry, paths, spend ceiling, and API keys loaded from environment."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent

# .env is never committed (see .gitignore); .env.example documents which keys
# are needed. override=False so a key already exported in the shell always
# wins over whatever .env has -- .env is a default, not an authority.
load_dotenv(ROOT_DIR / ".env", override=False)

CONFIG = {
    # "name" is the identifier written to log rows (row["model"]); "api_id" is
    # the exact string sent to the provider API. They can diverge if a
    # provider versions its api_id oddly.
    # Three study models, one per lab, approved to replace the original five
    # (claude-sonnet-5, gpt-5, gemini-2.5-pro, and the never-approved
    # llama-3.3-70b are all gone). Together AI is no longer a study provider
    # at all -- it's ranker-only now, see RANKER_MODELS below. IDs and prices
    # checked against each provider's own docs/pricing pages; rpm_limit is a
    # placeholder (not verified against account-specific tier limits) --
    # confirm in each console before the main run.
    #
    # daily_request_cap: the main run alone is 2,400 calls per model (6 items x
    # 4 levels x 2 arms x 50 runs), before pilot, the non-L0 pass, and preflight
    # are added on top -- so it's set to 4,000 per model, same for all three,
    # rather than tuned per model. This cap exists to catch a runaway loop
    # (e.g. a retry storm), not to bound spend -- that's total_spend_ceiling_usd's
    # job. Do not lower this as a cost-control measure; lower the spend ceiling
    # instead.
    "models": [
        {
            "name": "claude-haiku-4-5",
            "provider": "anthropic",
            "api_id": "claude-haiku-4-5",
            "price_per_million_in": 1.00,
            "price_per_million_out": 5.00,
            "rpm_limit": 50,
            "daily_request_cap": 4000,
        },
        {
            "name": "gpt-5.4-nano",
            "provider": "openai",
            "api_id": "gpt-5.4-nano",
            "price_per_million_in": 0.20,
            "price_per_million_out": 1.25,
            "rpm_limit": 50,
            "daily_request_cap": 4000,
        },
        {
            # TEST_MODEL (see below) -- cheapest of the three, not free.
            "name": "deepseek-v4-flash",
            "provider": "deepseek",
            "api_id": "deepseek-v4-flash",
            "price_per_million_in": 0.14,
            "price_per_million_out": 0.28,
            "rpm_limit": 50,
            "daily_request_cap": 4000,
        },
    ],
    "paths": {
        "items_file": ROOT_DIR / "items" / "items.yaml",
        "prompts_dir": ROOT_DIR / "items" / "prompts",
        "raw_dir": ROOT_DIR / "data" / "raw",
        # Single canonical log for every call this project makes — test,
        # preflight, pilot, and main-run rows all land here, distinguished by
        # call_context. They share it because they share the same real API
        # quota; splitting the file would make daily-budget accounting lie.
        "log_file": ROOT_DIR / "data" / "raw" / "run.jsonl",
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
}

assert CONFIG["temperature"] != 0, "temperature must never be 0 — it collapses repeated runs in a cell to n=1"

# Provider -> the environment variable its key lives in. This is the one place
# that mapping is declared; every key lookup in the repo goes through
# get_api_key() below rather than reading os.environ directly, so there is a
# single choke point to audit for accidental logging/printing of a value.
PROVIDER_API_KEY_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "together": "TOGETHER_API_KEY",
    "google": "GOOGLE_API_KEY",
}


def get_api_key(provider):
    """Reads a provider's API key from the environment at call time -- not a
    cached snapshot -- so a key set after this module was imported (e.g. dotenv
    picking up a .env edited mid-session) is still seen. Returns None if unset;
    never raises, never logs, never prints."""
    env_var = PROVIDER_API_KEY_ENV_VARS[provider]
    value = os.environ.get(env_var)
    return value if value else None


class MissingAPIKeyError(RuntimeError):
    """Raised by assert_api_keys_present. Message names only the missing
    environment variable(s) -- never a key value, not even masked."""


def models_by_name():
    """Model registry keyed by row["model"] name instead of list order."""
    return {m["name"]: m for m in CONFIG["models"]}


# No model in the current roster has a free tier (the one that did,
# gemini-2.5-pro, was removed). TEST_MODEL is therefore the cheapest paid
# model, not a free one -- accidental spend from a heavy test session is
# bounded by total_spend_ceiling_usd, not by daily_request_cap (see the comment
# on CONFIG["models"] above). Every script that isn't the pilot or the main
# run -- tests, preflight development, parser development, pipeline
# verification -- defaults to this model. Do NOT point this at a more
# expensive model for convenience; the other two are only ever called by the
# pilot and the main run.
TEST_MODEL = "deepseek-v4-flash"

# The three study models the pilot and main run iterate over. TEST_MODEL is
# one of these, but this stays a separate constant from TEST_MODEL on
# purpose: changing which model is used for cheap testing must never silently
# change which models the study actually runs, and vice versa.
EXPERIMENT_MODELS = [m["name"] for m in CONFIG["models"]]

assert TEST_MODEL in models_by_name(), f"TEST_MODEL {TEST_MODEL!r} is not in CONFIG['models']"
assert TEST_MODEL in EXPERIMENT_MODELS, "TEST_MODEL must be one of the study models"

# What kind of run produced a log row. "test" and "preflight" rows share the
# log file with "pilot" and "main" rows (see paths.log_file) but are not
# study data; verify_log.py excludes them from counts and spend by default.
# "manipulation_check" rows live in their own log (data/manipulation_check/raw.jsonl,
# see scripts/manipulation_check.py) but use the same schema and are listed here
# for the same reason: one registry of every valid call_context in the repo.
# "pilot_l0_recap" is the L0 re-probe of the four items whose max_tokens caps
# were raised after the first pilot showed 87-100% truncation. Kept distinct
# from "pilot" so those rows don't merge into the original Pass A results,
# which were collected under the old (binding) caps and are retained as-is.
CALL_CONTEXTS = ("test", "preflight", "pilot", "pilot_l0_recap", "pilot_l0_recap2", "pilot_l0_recap3", "pilot_l0_recap4", "main", "manipulation_check")
STUDY_CALL_CONTEXTS = ("pilot", "main")

# Rankers for scripts/manipulation_check.py: independent judges of whether the
# four observability levels actually read as differently evaluative. Both on
# Together AI, from labs with no other presence in this study (Meta is neither
# a study lab nor GLM's lab; GLM is Zhipu/Z.ai -- neither vendor appears in
# CONFIG["models"]). Kept as a separate registry, never merged into
# EXPERIMENT_MODELS: a ranker judging the item set must not also be a study
# subject answering it.
#
# IDs and rates below were checked against Together's public model pages; per
# scripts/manipulation_check.py's own instructions, confirm both again in the
# Together console before running, since providers change catalog IDs and
# prices without notice. The original second ranker, Qwen3-235B-A22B-Instruct
# on the -tput checkpoint, turned out not to be serverless despite its listing
# (100% HTTP 400 model_not_available across 120 calls -- it requires a
# dedicated endpoint) -- Llama-3.3-70B-Instruct-Turbo replaces it, confirmed
# serverless on its own Together model page, not inferred from the name.
# Llama-3.3-70B has no reasoning capability at all ("not_supported" --
# reasoning_disabled_by_for() falls through to this by default for any api_id
# not listed as "model_choice" or "api_parameter"). GLM-5.2 is a single
# checkpoint with thinking on by default, disabled only via a request
# parameter -- see reasoning_disabled_by_for() in
# src/providers/together_provider.py.
RANKER_MODELS = [
    {
        "name": "llama-3.3-70b",
        "provider": "together",
        "api_id": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
        "price_per_million_in": 1.04,
        "price_per_million_out": 1.04,
        "rpm_limit": 50,
        "daily_request_cap": 1000,
    },
    {
        "name": "glm-5.2",
        "provider": "together",
        "api_id": "zai-org/GLM-5.2",
        "price_per_million_in": 1.40,
        "price_per_million_out": 4.40,
        "rpm_limit": 50,
        "daily_request_cap": 1000,
    },
]


def rankers_by_name():
    return {m["name"]: m for m in RANKER_MODELS}


assert not set(rankers_by_name()) & set(EXPERIMENT_MODELS), "a ranker model must never also be a study model"


def assert_api_keys_present(model_names):
    """Verifies every key needed for `model_names` (row["model"] values -- from
    CONFIG["models"] and/or RANKER_MODELS) is present and non-empty. Call this at
    the start of any script that makes real API calls, before the first call, so
    a missing key fails immediately instead of partway through a run.

    Raises MissingAPIKeyError naming only the missing environment variable(s).
    Never includes a key value in the message, not even a masked one -- there is
    nothing to mask, since a missing key has no value to begin with.
    """
    registry = {**models_by_name(), **rankers_by_name()}
    missing = []
    for name in model_names:
        cfg = registry.get(name)
        if cfg is None:
            continue  # not this function's job to validate model names
        env_var = PROVIDER_API_KEY_ENV_VARS[cfg["provider"]]
        if not get_api_key(cfg["provider"]) and env_var not in missing:
            missing.append(env_var)
    if missing:
        raise MissingAPIKeyError(
            f"missing required API key(s): {', '.join(missing)}. Set them in .env or the environment."
        )


def key_status():
    """Presence (not value) of each provider's key, for display only."""
    return {provider: get_api_key(provider) is not None for provider in PROVIDER_API_KEY_ENV_VARS}


def print_key_status():
    """Prints a boolean-only presence table. Never prints any part of a key value."""
    status = key_status()
    width = max(len(p) for p in status)
    print(f"{'provider':<{width}}  key set")
    print(f"{'-' * width}  -------")
    for provider, present in status.items():
        print(f"{provider:<{width}}  {present}")


class WrongModelForTestError(RuntimeError):
    """Raised when a test/preflight/parser script targets a model other than TEST_MODEL."""


def assert_test_model(model_key):
    """Guard for every non-pilot, non-main-run script. Call this before making any API call."""
    if model_key != TEST_MODEL:
        raise WrongModelForTestError(
            f"{model_key!r} is not the test model ({TEST_MODEL!r}). Testing, preflight development, "
            "parser development, and pipeline verification all run on TEST_MODEL (the cheapest model "
            "in the roster, not a free one); the other study models are reserved for the pilot and "
            "the main run."
        )
