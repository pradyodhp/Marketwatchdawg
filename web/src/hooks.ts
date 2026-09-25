import { useEffect, useRef, useState } from 'react';

export function useCountUp(value: number, ms = 900) {
  const [v, setV] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    const start = performance.now(); const a = from.current; let raf = 0;
    const step = (now: number) => { const k = Math.min(1, (now - start) / ms); const e = 1 - Math.pow(1 - k, 3); setV(a + (value - a) * e); if (k < 1) raf = requestAnimationFrame(step); else from.current = value; };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value]);
  return v;
}
