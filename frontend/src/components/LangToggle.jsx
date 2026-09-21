import React from "react";
import { Globe } from "lucide-react";
import { useLang } from "@/contexts/LangContext";

export const LangToggle = () => {
  const { lang, toggleLang } = useLang();
  return (
    <button
      data-testid="language-toggle-button"
      onClick={toggleLang}
      aria-label="Language"
      className="anclora-toggle flex h-9 items-center gap-1.5 rounded-full px-3"
    >
      <Globe className="h-[16px] w-[16px]" strokeWidth={1.6} />
      <span className="text-[12.5px] font-bold tracking-wide">{lang.toUpperCase()}</span>
    </button>
  );
};
