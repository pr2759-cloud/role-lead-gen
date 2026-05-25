"""Cost-per-million-token reference. Update when Anthropic ships new models."""

# Prices in USD per million tokens (input, output).
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-7": (15.00, 75.00),
    "claude-haiku-4-5-20251001": (1.00, 5.00),
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """Return cost in USD. Falls back to Sonnet pricing for unknown models."""
    input_price, output_price = MODEL_PRICES.get(model, MODEL_PRICES["claude-sonnet-4-6"])
    return (input_tokens * input_price + output_tokens * output_price) / 1_000_000
