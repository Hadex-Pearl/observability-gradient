"""Provider adapter registry.

Every adapter exposes the same call signature:

    call(api_id, messages, *, max_tokens, temperature, reasoning_enabled, api_key) -> ProviderResponse

and raises ProviderError on failure. Adding a provider means writing one
adapter module with a `call` function and registering it in ADAPTERS below.
"""

from . import anthropic_provider, deepseek_provider, google_provider, openai_provider, together_provider

ADAPTERS = {
    "anthropic": anthropic_provider.call,
    "openai": openai_provider.call,
    "deepseek": deepseek_provider.call,
    "together": together_provider.call,
    "google": google_provider.call,
}


def get_adapter(provider):
    try:
        return ADAPTERS[provider]
    except KeyError:
        raise ValueError(f"no adapter registered for provider {provider!r}")
