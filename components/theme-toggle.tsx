"use client";

import React from "react";
import { Button } from "@/components/ui/button";

export function ThemeToggle({ asButton = false, expanded = true }: { asButton?: boolean; expanded?: boolean }): JSX.Element {
  const [isDark, setIsDark] = React.useState<boolean>(true);

  // Initialize from localStorage and current DOM state
  React.useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem("theme") : null;
    const prefersDark = document.body.classList.contains("dark");
    const initialDark = saved ? saved !== "light" : prefersDark;
    setIsDark(initialDark);
    apply(initialDark);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const apply = (dark: boolean) => {
    const cls = document.body.classList;
    if (dark) cls.add("dark");
    else cls.remove("dark");
    localStorage.setItem("theme", dark ? "dark" : "light");
  };

  const toggle = () => {
    setIsDark((v) => {
      const next = !v;
      apply(next);
      return next;
    });
  };

  if (asButton) {
    return (
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="rounded-full px-3 py-1 text-xs shadow-sm bg-background/70 backdrop-blur border-border hover:bg-accent gap-1.5"
        onClick={toggle}
        aria-label="Toggle theme"
      >
        {expanded ? (isDark ? "Dark" : "Light") : isDark ? "☾" : "☀︎"}
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-2 text-xs pl-1">
      <button
        onClick={toggle}
        className="relative inline-flex h-4 w-8 items-center rounded-full border border-input bg-background transition-colors"
        aria-label="Toggle theme"
      >
        <span
          className={`inline-block h-3.5 w-3.5 transform rounded-full bg-foreground transition-transform ${
            isDark ? "translate-x-4" : "translate-x-1"
          }`}
        />
      </button>
    </div>
  );
}


