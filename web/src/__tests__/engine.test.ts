import { describe, expect, it } from 'vitest';
import { parseCsv, pctStr, price, splitCsvBySymbol, tier } from '../engine';

const CSV = [
  'datetime,symbol,open,high,low,close,volume',
  '2026-09-24 09:15:00,AAA,100,101,99,100.5,1000',
  '2026-09-24 09:20:00,AAA,100.5,102,100,101.5,1200',
  '2026-09-24 09:15:00,BBB,50,50.5,49.5,50.2,500',
  '2026-09-24 09:20:00,BBB,abc,50.5,49.5,50.2,500',
  '2026-09-24 09:25:00,BBB,50,50.5,49.5,50.2,-3',
].join('\n');

describe('parseCsv', () => {
  it('groups valid rows by symbol and reports dropped rows', () => {
    const out = parseCsv(CSV);
    expect(out.series.AAA).toHaveLength(2);
    expect(out.series.BBB).toHaveLength(1);
    expect(out.dropped).toHaveLength(2);
    expect(out.dropped[0].why).toMatch(/non-numeric/);
    expect(out.dropped[1].why).toMatch(/negative volume/);
  });
  it('rejects files without required columns', () => {
    expect(() => parseCsv('a,b\n1,2')).toThrow(/Missing column/);
  });
});

describe('splitCsvBySymbol', () => {
  it('keeps raw datetimes and builds ingest-ready single-symbol CSVs', () => {
    const parts = splitCsvBySymbol(CSV);
    const aaa = parts.find(p => p.symbol === 'AAA')!;
    expect(aaa.rows).toBe(2);
    expect(aaa.csv.split('\n')[0]).toBe('datetime,open,high,low,close,volume');
    expect(aaa.csv).toContain('2026-09-24 09:15:00,100,101,99,100.5,1000');
    expect(parts.find(p => p.symbol === 'BBB')!.rows).toBe(3);
  });
});

describe('formatting', () => {
  it('tiers and price formats', () => {
    expect(tier(90)).toBe('crit');
    expect(tier(75)).toBe('high');
    expect(tier(55)).toBe('med');
    expect(tier(10)).toBe('low');
    expect(pctStr(1.234)).toBe('+1.23%');
    expect(pctStr(-2)).toBe('-2.00%');
    expect(price(2915.4)).toBe('2,915');
    expect(price(23.4)).toBe('23.40');
  });
});
