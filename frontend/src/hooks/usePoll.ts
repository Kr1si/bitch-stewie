import { useCallback, useEffect, useRef } from "react";

/** Poll a loader at `intervalMs` until the component unmounts. */
export function usePoll<T>(loader: () => Promise<T>, intervalMs = 10000, deps: unknown[] = []) {
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const cb = useCallback(loader, deps);
  const ref = useRef(cb);
  ref.current = cb;
  useEffect(() => {
    let active = true;
    const tick = () => ref.current().catch(() => {}).finally(() => {
      if (active) t = window.setTimeout(tick, intervalMs);
    });
    let t = window.setTimeout(tick, 0);
    return () => { active = false; clearTimeout(t); };
  }, [intervalMs]);
}