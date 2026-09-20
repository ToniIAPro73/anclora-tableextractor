import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { translations } from "@/i18n/translations";

const LangContext = createContext(null);

export const LangProvider = ({ children }) => {
  const [lang, setLang] = useState(() => localStorage.getItem("anclora_lang") || "es");

  useEffect(() => {
    localStorage.setItem("anclora_lang", lang);
    document.documentElement.lang = lang;
  }, [lang]);

  const toggleLang = useCallback(() => {
    setLang((prev) => (prev === "es" ? "en" : "es"));
  }, []);

  const t = useCallback(
    (path) => {
      const parts = path.split(".");
      let node = translations[lang];
      for (const p of parts) {
        node = node?.[p];
      }
      return node ?? path;
    },
    [lang]
  );

  return (
    <LangContext.Provider value={{ lang, setLang, toggleLang, t }}>
      {children}
    </LangContext.Provider>
  );
};

export const useLang = () => {
  const ctx = useContext(LangContext);
  if (!ctx) throw new Error("useLang must be used within LangProvider");
  return ctx;
};
