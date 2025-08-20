"use client";

import React from "react";

export function ThemeToggle(): JSX.Element {
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

  return (
    <div className="flex items-center gap-3 text-xs pl-2">
      <span className="select-none text-muted-foreground">{isDark ? "Dark" : "Light"}</span>
      <button
        onClick={toggle}
        className="relative inline-flex h-5 w-10 items-center rounded-full border border-input bg-background transition-colors"
        aria-label="Toggle theme"
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-foreground transition-transform ${
            isDark ? "translate-x-5" : "translate-x-1.5"
          }`}
        />
      </button>
    </div>
  );
}


