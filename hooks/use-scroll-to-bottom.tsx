import { useEffect, useRef, type RefObject } from "react";

export function useScrollToBottom<T extends HTMLElement>(offsetPx: number = 100): [
  RefObject<T>,
  RefObject<T>,
] {
  const containerRef = useRef<T>(null);
  const endRef = useRef<T>(null);

  useEffect(() => {
    const container = containerRef.current;
    const end = endRef.current;

    if (container && end) {
      const observer = new MutationObserver(() => {
        const endEl = endRef.current as unknown as HTMLElement | null;
        if (!endEl) return;
        const rect = endEl.getBoundingClientRect();
        const targetY = window.scrollY + rect.top - offsetPx;
        window.scrollTo({ top: Math.max(0, targetY), behavior: "smooth" });
      });

      observer.observe(container, {
        childList: true,
        subtree: true,
        attributes: true,
        characterData: true,
      });

      return () => observer.disconnect();
    }
  }, [offsetPx]);

  return [containerRef, endRef];
}
