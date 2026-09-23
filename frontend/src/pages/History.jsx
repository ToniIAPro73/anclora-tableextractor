import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { History as HistoryIcon, FileText, Trash2, ArrowRight, Loader2, UploadCloud, Sheet, FileJson, X, Download } from "lucide-react";
import { toast } from "sonner";
import { Header } from "@/components/Header";
import { useLang } from "@/contexts/LangContext";
import { api } from "@/lib/api";
import { Checkbox } from "@/components/ui/checkbox";

const HistoryStatusBadge = ({ estado, t }) => {
  const tone = {
    pendiente: "warning",
    validado: "success",
    exportado: "info",
  }[estado] || "muted";

  return (
    <span data-testid={`status-badge-${estado}`} className={`ac-status-badge ac-status-badge--${tone}`}>
      {t(`history.${estado}`)}
    </span>
  );
};

const ThumbCell = ({ docId }) => {
  const [url, setUrl] = useState(null);
  const [failed, setFailed] = useState(false);
  useEffect(() => {
    let objUrl;
    let active = true;
    api.get(`/documents/${docId}/thumbnail`, { responseType: "blob" })
      .then((res) => {
        if (!active) return;
        objUrl = URL.createObjectURL(res.data);
        setUrl(objUrl);
      })
      .catch(() => active && setFailed(true));
    return () => { active = false; if (objUrl) URL.revokeObjectURL(objUrl); };
  }, [docId]);

  return (
    <div data-testid={`thumb-${docId}`} className="history-table__thumbnail">
      {url ? (
        <img src={url} alt="pdf" className="h-full w-full object-cover object-top" />
      ) : (
        <FileText className={`h-5 w-5 ${failed ? "text-muted-foreground" : "text-red-500 animate-pulse"}`} />
      )}
    </div>
  );
};

export default function HistoryPage() {
  const { t, lang } = useLang();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [docs, setDocs] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [batchLoading, setBatchLoading] = useState(null);

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

  const toggle = (id) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const toggleAll = () => {
    setSelected((prev) => (prev.size === docs.length ? new Set() : new Set(docs.map((d) => d.id))));
  };

  const batchExport = async (format) => {
    setBatchLoading(format);
    try {
      const res = await api.post("/documents/export-batch", { doc_ids: Array.from(selected), format }, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = format === "xlsx" ? "anclora_export.xlsx" : `anclora_export_${format}.zip`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setDocs((prev) => prev.map((d) => (selected.has(d.id) ? { ...d, estado: "exportado" } : d)));
      toast.success(t("toast.batchExported"));
    } catch (e) {
      toast.error(e?.response?.data?.detail || t("toast.error"));
    } finally {
      setBatchLoading(null);
    }
  };

  const remove = async (id) => {
    if (!window.confirm(t("history.deleteConfirm"))) return;
    try {
      await api.delete(`/documents/${id}`);
      setDocs((prev) => prev.filter((d) => d.id !== id));
      setSelected((prev) => { const n = new Set(prev); n.delete(id); return n; });
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

  const allSelected = docs.length > 0 && selected.size === docs.length;
  const someSelected = selected.size > 0 && !allSelected;

  return (
    <div className="anclora-ds-scope min-h-screen bg-background">
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
          <div data-testid="history-empty" className="ac-empty-state mt-10">
            <FileText className="h-10 w-10 text-muted-foreground" strokeWidth={1.4} />
            <p className="ac-empty-state__summary">{t("history.empty")}</p>
            <button onClick={() => navigate("/upload")} className="ac-button ac-button--primary">
              <UploadCloud className="h-4 w-4" /> {t("history.goUpload")}
            </button>
          </div>
        ) : (
          <>
            {selected.size > 0 && (
              <div data-testid="batch-export-bar" className="history-table__bulk-bar fade-up">
                <div className="flex items-center gap-2 text-sm font-semibold">
                  <Download className="h-4 w-4 text-primary" />
                  {selected.size} {t("history.selected")}
                  <button data-testid="clear-selection-button" onClick={() => setSelected(new Set())} className="ac-button ac-button--secondary ac-button--compact ml-2">
                    <X className="h-3 w-3" /> {t("history.clearSelection")}
                  </button>
                </div>
                <div className="history-table__bulk-actions">
                  {[
                    { fmt: "xlsx", label: t("history.batchExportXlsx"), icon: Sheet },
                    { fmt: "csv", label: t("history.batchExportCsv"), icon: FileText },
                    { fmt: "json", label: t("history.batchExportJson"), icon: FileJson },
                  ].map(({ fmt, label, icon: Icon }) => (
                    <button
                      key={fmt}
                      data-testid={`batch-export-${fmt}-button`}
                      onClick={() => batchExport(fmt)}
                      disabled={batchLoading !== null}
                      className="ac-button ac-button--primary ac-button--compact"
                    >
                      {batchLoading === fmt ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="ac-data-table mt-6 fade-up">
            <div className="ac-data-table__scroll thin-scroll" role="region" tabIndex="0" aria-label={t("history.tableLabel")}>
              <table>
                <caption className="sr-only">{t("history.tableLabel")}</caption>
                <thead>
                  <tr>
                    <th scope="col" data-align="center">
                      <Checkbox
                        data-testid="select-all-checkbox"
                        checked={allSelected ? true : someSelected ? "indeterminate" : false}
                        onCheckedChange={toggleAll}
                        aria-label={t("history.selectAll")}
                      />
                    </th>
                    <th scope="col">{t("history.name")}</th>
                    <th scope="col">{t("history.date")}</th>
                    <th scope="col" data-align="center">{t("history.pages")}</th>
                    <th scope="col" data-align="center">{t("history.tables")}</th>
                    <th scope="col">{t("history.status")}</th>
                    <th scope="col" data-column="actions">{t("history.actions")}</th>
                  </tr>
                </thead>
                <tbody>
                  {docs.map((d) => (
                    <tr key={d.id} data-testid={`history-row-${d.id}`} data-selected={selected.has(d.id) ? "true" : undefined} data-interactive="true">
                      <td data-align="center">
                        <Checkbox
                          data-testid={`select-doc-${d.id}`}
                          checked={selected.has(d.id)}
                          onCheckedChange={() => toggle(d.id)}
                          aria-label={t("history.selectDocument").replace("{name}", d.nombre_archivo)}
                        />
                      </td>
                      <th scope="row">
                        <div className="history-table__document">
                          <ThumbCell docId={d.id} />
                          <span className="history-table__document-name">{d.nombre_archivo}</span>
                        </div>
                      </th>
                      <td>{fmtDate(d.fecha_carga)}</td>
                      <td data-align="center">{d.num_paginas}</td>
                      <td data-align="center">{d.num_tablas}</td>
                      <td><HistoryStatusBadge estado={d.estado} t={t} /></td>
                      <td data-column="actions">
                        <div className="ac-data-table__actions">
                          <button
                            data-testid={`review-doc-${d.id}`}
                            onClick={() => navigate(`/review/${d.id}`)}
                            className="ac-button ac-button--secondary ac-button--compact"
                          >
                            {t("history.review")} <ArrowRight className="h-3.5 w-3.5" />
                          </button>
                          <button
                            data-testid={`delete-doc-${d.id}`}
                            onClick={() => remove(d.id)}
                            className="ac-button ac-button--destructive ac-button--compact ac-button--icon"
                            aria-label={`${t("history.delete")} ${d.nombre_archivo}`}
                          >
                            <Trash2 className="ac-button__icon h-4 w-4" aria-hidden="true" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
