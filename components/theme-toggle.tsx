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
    <div className="fixed right-4 top-4 z-50 flex items-center gap-2 text-sm">
      <span className="select-none">{isDark ? "Dark" : "Light"}</span>
      <button
        onClick={toggle}
        className="rounded border px-2 py-1 hover:bg-muted"
        aria-label="Toggle theme"
      >
        Toggle
      </button>
    </div>
  );
}


