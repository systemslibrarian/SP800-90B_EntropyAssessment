"""py90b: independent Python reference implementations of SP 800-90B (Jan 2018)
estimators, written from the standard's text only (see AUDIT-BRIEF.md).

Each module exposes estimate(symbols, bits_per_symbol, **options) -> dict and a
__main__ that reads a raw byte file and prints that dict as JSON.
"""
