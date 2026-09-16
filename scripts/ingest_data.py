#!/usr/bin/env python
"""Offline data curation script — pre-fetches 60 days of 5-minute NIFTY 100 candles.

Usage:
    python scripts/ingest_data.py [--dry-run] [--symbols SYM1 SYM2 ...]

Writes curated Parquet files to data/curated/ and a quality_metadata.json summary.
This script is ONLY for offline data acquisition.  Never import it during replay.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure repo src is importable when run directly
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from marketwatch.config.universe import load_universe_config
from marketwatch.ingestion.fetcher import fetch_universe
from marketwatch.ingestion.validator import validate_ohlcv
from marketwatch.ingestion.parquet_store import (
    DEFAULT_CURATED_DIR,
    write_symbol_parquet,
    write_quality_metadata,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest")


def main() -> int:
    parser = argparse.ArgumentParser(description="NIFTY 100 offline data curation")
    parser.add_argument("--dry-run", action="store_true", help="Fetch but do not write Parquet")
    parser.add_argument("--symbols", nargs="+", help="Override symbol list (for testing)")
    parser.add_argument("--curated-dir", default=str(DEFAULT_CURATED_DIR), help="Output directory")
    parser.add_argument("--benchmarks-only", action="store_true", help="Only fetch benchmarks")
    args = parser.parse_args()

    curated_dir = Path(args.curated_dir)

    # ── Load universe ─────────────────────────────────────────────────────────
    cfg = load_universe_config()
    equity_symbols = cfg.get_symbols()

    # Collect benchmark symbols
    benchmark_symbols = [cfg.benchmarks.broad.symbol]
    for sb in cfg.benchmarks.sectors.values():
        if sb.symbol not in benchmark_symbols:
            benchmark_symbols.append(sb.symbol)

    if args.benchmarks_only:
        all_symbols = benchmark_symbols
    elif args.symbols:
        all_symbols = args.symbols
    else:
        all_symbols = equity_symbols + benchmark_symbols

    logger.info("Targets: %d symbols (%d equities + %d benchmarks)",
                len(all_symbols), len(equity_symbols), len(benchmark_symbols))

    # ── Fetch ─────────────────────────────────────────────────────────────────
    results = fetch_universe(all_symbols)

    # ── Validate + Write ──────────────────────────────────────────────────────
    loaded_symbols: list[str] = []
    missing_symbols: list[str] = []
    date_starts: list[str] = []
    date_ends: list[str] = []
    total_rows_written = 0
    symbol_coverage: dict[str, dict] = {}

    for result in results:
        if not result.success or result.df is None:
            logger.warning("MISSING  %s — reason: %s", result.symbol, result.error)
            missing_symbols.append(result.symbol)
            symbol_coverage[result.symbol] = {"status": "missing", "reason": result.error}
            continue

        clean_df, val_result = validate_ohlcv(result.symbol, result.df)

        if clean_df.empty:
            logger.warning("EMPTY-AFTER-VALIDATION  %s", result.symbol)
            missing_symbols.append(result.symbol)
            symbol_coverage[result.symbol] = {
                "status": "empty_after_validation",
                "dropped_reasons": val_result.invalid_reasons,
            }
            continue

        if not args.dry_run:
            write_symbol_parquet(result.symbol, clean_df, curated_dir)

        loaded_symbols.append(result.symbol)
        total_rows_written += val_result.valid_rows
        date_starts.append(val_result.date_range[0])
        date_ends.append(val_result.date_range[1])
        symbol_coverage[result.symbol] = {
            "status": "ok",
            "rows": val_result.valid_rows,
            "trading_days": val_result.trading_days,
            "date_range": list(val_result.date_range),
            "zero_volume_rows": val_result.zero_volume_rows,
            "dropped_rows": val_result.dropped_rows,
            "dropped_reasons": val_result.invalid_reasons,
        }

    # ── Build quality metadata ────────────────────────────────────────────────
    n_requested = len(all_symbols)
    n_loaded = len(loaded_symbols)
    coverage_pct = round(100 * n_loaded / n_requested, 2) if n_requested else 0.0
    date_range_start = min(date_starts) if date_starts else ""
    date_range_end = max(date_ends) if date_ends else ""

    quality_metadata = {
        "requested_symbols": all_symbols,
        "loaded_symbols": loaded_symbols,
        "missing_symbols": missing_symbols,
        "n_requested": n_requested,
        "n_loaded": n_loaded,
        "coverage_pct": coverage_pct,
        "total_rows": total_rows_written,
        "date_range_start": date_range_start,
        "date_range_end": date_range_end,
        "dry_run": args.dry_run,
        "symbol_coverage": symbol_coverage,
    }

    if not args.dry_run:
        write_quality_metadata(quality_metadata, curated_dir)
    else:
        logger.info("DRY RUN — metadata not written")
        print(json.dumps(quality_metadata, indent=2))

    # ── Summary ───────────────────────────────────────────────────────────────
    logger.info("=" * 60)
    logger.info("INGESTION COMPLETE")
    logger.info("  Requested : %d symbols", n_requested)
    logger.info("  Loaded    : %d symbols (%.1f%%)", n_loaded, coverage_pct)
    logger.info("  Missing   : %d symbols", len(missing_symbols))
    logger.info("  Rows      : %d", total_rows_written)
    logger.info("  Date range: %s → %s", date_range_start, date_range_end)
    if missing_symbols:
        logger.warning("  Missing symbols: %s", missing_symbols[:20])
    logger.info("=" * 60)

    return 0 if n_loaded > 0 else 1


if __name__ == "__main__":
    sys.exit(main())
