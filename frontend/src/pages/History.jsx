import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { History as HistoryIcon, FileText, Trash2, ArrowRight, Loader2, UploadCloud } from "lucide-react";
import { toast } from "sonner";
import { Header } from "@/components/Header";
import { StatusBadge } from "@/pages/Review";
import { useLang } from "@/contexts/LangContext";
import { api } from "@/lib/api";

export default function HistoryPage() {
  const { t, lang } = useLang();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [docs, setDocs] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/documents");
      setDocs(res.data.documents);
    } catch (e) {
      toast.error(t("toast.error"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => { load(); }, [load]);

  const remove = async (id) => {
    if (!window.confirm(t("history.deleteConfirm"))) return;
    try {
      await api.delete(`/documents/${id}`);
      setDocs((prev) => prev.filter((d) => d.id !== id));
      toast.success(t("toast.deleted"));
    } catch (e) {
      toast.error(t("toast.error"));
    }
  };

  const fmtDate = (iso) => {
    try {
      return new Date(iso).toLocaleString(lang === "es" ? "es-ES" : "en-US", {
        year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
      });
    } catch { return iso; }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="fade-up flex items-center gap-3">
          <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10">
            <HistoryIcon className="h-5 w-5 text-primary" strokeWidth={1.7} />
          </span>
          <div>
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl" style={{ fontFamily: "Manrope, sans-serif" }}>{t("history.title")}</h1>
            <p className="mt-1 text-sm text-muted-foreground">{t("history.subtitle")}</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-32"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
        ) : docs.length === 0 ? (
          <div data-testid="history-empty" className="mt-10 flex flex-col items-center justify-center rounded-2xl border border-dashed border-border py-20 text-center">
            <FileText className="h-10 w-10 text-muted-foreground" strokeWidth={1.4} />
            <p className="mt-4 text-sm text-muted-foreground">{t("history.empty")}</p>
            <button onClick={() => navigate("/upload")} className="mt-5 flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25">
              <UploadCloud className="h-4 w-4" /> {t("history.goUpload")}
            </button>
          </div>
        ) : (
          <div className="mt-6 overflow-hidden rounded-2xl border border-border bg-card fade-up">
            <div className="overflow-x-auto thin-scroll">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border bg-muted/50 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    <th className="px-4 py-3">{t("history.name")}</th>
                    <th className="px-4 py-3">{t("history.date")}</th>
                    <th className="px-4 py-3 text-center">{t("history.pages")}</th>
                    <th className="px-4 py-3 text-center">{t("history.tables")}</th>
                    <th className="px-4 py-3">{t("history.status")}</th>
                    <th className="px-4 py-3 text-right">{t("history.actions")}</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((d) => (
                    <tr key={d.id} data-testid={`history-row-${d.id}`} className="border-b border-border last:border-0 hover:bg-muted/30">
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2.5">
                          <FileText className="h-4 w-4 shrink-0 text-red-500" />
                          <span className="font-medium">{d.nombre_archivo}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-muted-foreground">{fmtDate(d.fecha_carga)}</td>
                      <td className="px-4 py-3 text-center">{d.num_paginas}</td>
                      <td className="px-4 py-3 text-center">{d.num_tablas}</td>
                      <td className="px-4 py-3"><StatusBadge estado={d.estado} t={t} /></td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            data-testid={`review-doc-${d.id}`}
                            onClick={() => navigate(`/review/${d.id}`)}
                            className="flex items-center gap-1.5 rounded-full border border-primary/40 px-3 py-1.5 text-xs font-semibold text-primary transition hover:bg-primary/10"
                          >
                            {t("history.review")} <ArrowRight className="h-3.5 w-3.5" />
                          </button>
                          <button
                            data-testid={`delete-doc-${d.id}`}
                            onClick={() => remove(d.id)}
                            className="rounded-full p-2 text-muted-foreground transition hover:bg-destructive/10 hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
