"""Parquet read/write layer for curated OHLCV candle data.

Storage layout:
    data/curated/
        {SYMBOL}.parquet         (one file per ticker, sorted by Datetime)
        quality_metadata.json    (dataset-level coverage summary)

Parquet schema (pyarrow):
    Datetime   : timestamp[ns, tz=Asia/Kolkata]
    symbol     : string
    open       : double
    high       : double
    low        : double
    close      : double
    volume     : double
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

logger = logging.getLogger(__name__)

DEFAULT_CURATED_DIR = Path("data/curated")

# PyArrow schema — strict, typed, IST-aware
CANDLE_SCHEMA = pa.schema([
    pa.field("Datetime", pa.timestamp("ns", tz="Asia/Kolkata")),
    pa.field("symbol",   pa.string()),
    pa.field("open",     pa.float64()),
    pa.field("high",     pa.float64()),
    pa.field("low",      pa.float64()),
    pa.field("close",    pa.float64()),
    pa.field("volume",   pa.float64()),
])


def write_symbol_parquet(
    symbol: str,
    df: pd.DataFrame,
    curated_dir: Path = DEFAULT_CURATED_DIR,
) -> Path:
    """Write a validated OHLCV DataFrame to {curated_dir}/{symbol}.parquet.

    Args:
        symbol: Ticker string (used as filename).
        df: Validated DataFrame with IST DatetimeIndex and columns Open/High/Low/Close/Volume.
        curated_dir: Target directory.

    Returns:
        Path to the written Parquet file.
    """
    curated_dir.mkdir(parents=True, exist_ok=True)

    # Normalise column names to lowercase for the Parquet schema
    out = df.rename(columns={"Open": "open", "High": "high", "Low": "low",
                              "Close": "close", "Volume": "volume"}).copy()
    out.index.name = "Datetime"
    out = out.reset_index()
    out.insert(1, "symbol", symbol)

    # Cast to schema types
    out["open"]   = out["open"].astype("float64")
    out["high"]   = out["high"].astype("float64")
    out["low"]    = out["low"].astype("float64")
    out["close"]  = out["close"].astype("float64")
    out["volume"] = out["volume"].astype("float64")

    table = pa.Table.from_pandas(out, schema=CANDLE_SCHEMA, preserve_index=False)
    safe_name = symbol.replace("^", "_CARET_").replace(".", "_")
    parquet_path = curated_dir / f"{safe_name}.parquet"
    pq.write_table(table, parquet_path, compression="snappy")
    logger.info("[%s] Written %d rows → %s", symbol, len(out), parquet_path)
    return parquet_path


def read_symbol_parquet(
    symbol: str,
    curated_dir: Path = DEFAULT_CURATED_DIR,
) -> pd.DataFrame | None:
    """Read a single symbol's Parquet file.  Returns None if file not found.

    Args:
        symbol: Ticker string.
        curated_dir: Directory containing curated Parquet files.

    Returns:
        DataFrame with IST DatetimeIndex and columns open/high/low/close/volume, or None.
    """
    safe_name = symbol.replace("^", "_CARET_").replace(".", "_")
    parquet_path = curated_dir / f"{safe_name}.parquet"

    if not parquet_path.exists():
        logger.debug("[%s] Parquet file not found: %s", symbol, parquet_path)
        return None

    table = pq.read_table(parquet_path)
    df = table.to_pandas()
    df = df.set_index("Datetime").drop(columns=["symbol"], errors="ignore")
    df.index = pd.DatetimeIndex(df.index).tz_convert("Asia/Kolkata")
    df = df.sort_index()
    return df


def list_available_symbols(curated_dir: Path = DEFAULT_CURATED_DIR) -> list[str]:
    """Return symbols for which curated Parquet files exist."""
    if not curated_dir.exists():
        return []
    symbols = []
    for p in sorted(curated_dir.glob("*.parquet")):
        name = p.stem
        # Reverse safe naming
        name = name.replace("_CARET_", "^").replace("_NS", ".NS")
        # Reload from metadata if available
        symbols.append(p.stem)  # store safe name; caller resolves if needed
    return symbols


def write_quality_metadata(
    metadata: dict,
    curated_dir: Path = DEFAULT_CURATED_DIR,
) -> Path:
    """Write quality metadata dict to quality_metadata.json."""
    curated_dir.mkdir(parents=True, exist_ok=True)
    metadata["generated_at"] = datetime.now(tz=timezone.utc).isoformat()
    out_path = curated_dir / "quality_metadata.json"
    out_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    logger.info("Quality metadata written → %s", out_path)
    return out_path


def read_quality_metadata(curated_dir: Path = DEFAULT_CURATED_DIR) -> dict | None:
    """Read quality_metadata.json; return None if not found."""
    p = curated_dir / "quality_metadata.json"
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
