import React from "react";
import { Sun, Moon } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";

export const ThemeToggle = () => {
  const { resolvedDark, setTheme } = useTheme();
  const isDark = resolvedDark();
  const ActiveIcon = isDark ? Moon : Sun;

  return (
    <button
      data-testid="theme-toggle-button"
      aria-label={isDark ? "Switch to light theme" : "Switch to dark theme"}
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className="anclora-toggle flex h-9 w-9 items-center justify-center rounded-full"
    >
      <ActiveIcon className="h-[18px] w-[18px]" strokeWidth={1.6} />
    </button>
  );
};
