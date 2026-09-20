import React from "react";
import { Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "@/contexts/ThemeContext";
import { useLang } from "@/contexts/LangContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const labels = {
  es: { light: "Claro", dark: "Oscuro", system: "Sistema" },
  en: { light: "Light", dark: "Dark", system: "System" },
};

export const ThemeToggle = () => {
  const { theme, setTheme, resolvedDark } = useTheme();
  const { lang } = useLang();
  const l = labels[lang];
  const ActiveIcon = resolvedDark() ? Moon : Sun;

  const options = [
    { key: "light", icon: Sun, label: l.light },
    { key: "dark", icon: Moon, label: l.dark },
    { key: "system", icon: Monitor, label: l.system },
  ];

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          data-testid="theme-toggle-button"
          aria-label="Theme"
          className="anclora-toggle flex h-9 w-9 items-center justify-center rounded-full"
        >
          <ActiveIcon className="h-[18px] w-[18px]" strokeWidth={1.6} />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="min-w-[9rem]">
        {options.map((opt) => {
          const Icon = opt.icon;
          return (
            <DropdownMenuItem
              key={opt.key}
              data-testid={`theme-option-${opt.key}`}
              onClick={() => setTheme(opt.key)}
              className={`gap-2 cursor-pointer ${theme === opt.key ? "text-primary font-semibold" : ""}`}
            >
              <Icon className="h-4 w-4" strokeWidth={1.6} />
              {opt.label}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
