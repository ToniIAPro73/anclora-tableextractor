import React, { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  FileSpreadsheet, Filter, CheckCircle2, Download, Loader2,
  FileJson, FileText, Sheet, Layers, ScanText, Type, FileStack,
} from "lucide-react";
import { toast } from "sonner";
import { Header } from "@/components/Header";
import { ConfidenceGrid, confClass } from "@/components/ConfidenceGrid";
import { useLang } from "@/contexts/LangContext";
import { api } from "@/lib/api";
import { loadPdfFromDocId } from "@/lib/pdf";

const countDoubtful = (tables) =>
  tables.reduce((acc, t) => acc + t.cells.filter((c) => c.score_confianza < 0.9).length, 0);

export default function Review() {
  const { docId } = useParams();
  const { t, lang } = useLang();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [doc, setDoc] = useState(null);
  const [tables, setTables] = useState([]);
  const [onlyDoubtful, setOnlyDoubtful] = useState(false);
  const [downloading, setDownloading] = useState(null);
  const [pdf, setPdf] = useState(null);

  const load = useCallback(async () => {
    if (!docId) { setLoading(false); return; }
    setLoading(true);
    try {
      const res = await api.get(`/documents/${docId}`);
      setDoc(res.data.documento);
      setTables(res.data.tablas);
    } catch (e) {
      toast.error(t("toast.error"));
    } finally {
      setLoading(false);
    }
    loadPdfFromDocId(docId).then(setPdf).catch(() => setPdf(null));
  }, [docId, t]);

  useEffect(() => { load(); }, [load]);
  useEffect(() => () => { if (pdf) pdf.destroy?.(); }, [pdf]);

  const handleColumnTypeChange = async (tableId, columna, tipo) => {
    try {
      const res = await api.put(`/documents/${docId}/column-type`, { table_id: tableId, columna, tipo });
      const updatedById = {};
      res.data.cells.forEach((c) => { updatedById[`${c.fila}-${c.columna}`] = c; });
      setTables((prev) =>
        prev.map((tb) =>
          tb.id !== tableId ? tb : {
            ...tb,
            column_types: res.data.column_types,
            cells: tb.cells.map((c) =>
              c.columna === columna ? (updatedById[`${c.fila}-${c.columna}`] || c) : c
            ),
          }
        )
      );
      toast.success(t("toast.typeChanged"));
    } catch (e) {
      toast.error(e?.response?.data?.detail || t("toast.error"));
    }
  };

  const handleCellSave = async (tableId, fila, columna, valor) => {
    try {
      await api.put(`/documents/${docId}/cell`, { table_id: tableId, fila, columna, valor });
      setTables((prev) =>
        prev.map((tb) =>
          tb.id !== tableId ? tb : {
            ...tb,
            cells: tb.cells.map((c) =>
              c.fila === fila && c.columna === columna
                ? { ...c, valor, score_confianza: 1.0, edited: true }
                : c
            ),
          }
        )
      );
      toast.success(t("toast.cellSaved"));
    } catch (e) {
      toast.error(t("toast.error"));
    }
  };

  const validate = async () => {
    try {
      await api.post(`/documents/${docId}/validate`);
      setDoc((d) => ({ ...d, estado: "validado" }));
      toast.success(t("toast.validated"));
    } catch (e) {
      toast.error(t("toast.error"));
    }
  };

  const download = async (format) => {
    setDownloading(format);
    try {
      const res = await api.get(`/documents/${docId}/export?format=${format}`, { responseType: "blob" });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const a = document.createElement("a");
      const base = (doc?.nombre_archivo || "export").replace(/\.pdf$/i, "");
      a.href = url;
      a.download = `${base}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
      setDoc((d) => ({ ...d, estado: "exportado" }));
      toast.success(t("toast.exported"));
    } catch (e) {
      toast.error(t("toast.error"));
    } finally {
      setDownloading(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <div className="flex items-center justify-center py-40"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
      </div>
    );
  }

  if (!docId || !doc) {
    return (
      <div className="min-h-screen bg-background">
        <Header />
        <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl" style={{ fontFamily: "Manrope, sans-serif" }}>{t("review.title")}</h1>
          <div data-testid="no-doc-state" className="mt-10 flex flex-col items-center justify-center rounded-2xl border border-dashed border-border py-20 text-center">
            <FileSpreadsheet className="h-10 w-10 text-muted-foreground" strokeWidth={1.4} />
            <p className="mt-4 text-sm text-muted-foreground">{t("review.noDoc")}</p>
            <button onClick={() => navigate("/history")} className="mt-4 rounded-full border border-primary/40 px-4 py-2 text-sm font-semibold text-primary hover:bg-primary/10">
              {t("nav.history")}
            </button>
          </div>
        </main>
      </div>
    );
  }

  const doubtful = countDoubtful(tables);
  const exportFmts = [
    { fmt: "xlsx", label: t("exportPanel.xlsx"), icon: Sheet },
    { fmt: "csv", label: t("exportPanel.csv"), icon: FileText },
    { fmt: "json", label: t("exportPanel.json"), icon: FileJson },
  ];

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="fade-up flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight sm:text-3xl" style={{ fontFamily: "Manrope, sans-serif" }}>{doc.nombre_archivo}</h1>
            <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
              <span className="flex items-center gap-1.5"><FileStack className="h-4 w-4" /> {doc.num_paginas} {t("upload.pages")}</span>
              <span className="flex items-center gap-1.5"><Layers className="h-4 w-4" /> {tables.length} {t("upload.tables")}</span>
              <StatusBadge estado={doc.estado} t={t} />
            </p>
          </div>
        </div>

        {/* Toolbar */}
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-card p-4">
          <div className="flex flex-wrap items-center gap-3">
            <button
              data-testid="filter-doubtful-cells-button"
              onClick={() => setOnlyDoubtful((v) => !v)}
              className={`flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition ${
                onlyDoubtful ? "border-primary bg-primary/10 text-primary" : "border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              <Filter className="h-4 w-4" /> {t("review.onlyDoubtful")}
            </button>
            <span data-testid="doubtful-counter" className="text-sm">
              {doubtful > 0 ? (
                <span className="font-semibold text-amber-500">{doubtful} {t("review.doubtfulLeft")}</span>
              ) : (
                <span className="flex items-center gap-1.5 font-semibold text-emerald-500"><CheckCircle2 className="h-4 w-4" /> {t("review.allValidated")}</span>
              )}
            </span>
          </div>
          <Legend t={t} />
        </div>

        {/* Tables */}
        {tables.length === 0 ? (
          <div className="mt-8 rounded-2xl border border-dashed border-border py-16 text-center text-sm text-muted-foreground">
            {t("review.noTables")}
          </div>
        ) : (
          <div className="mt-6 space-y-8">
            {tables.map((table, ti) => (
              <div key={table.id} className="fade-up">
                <div className="mb-3 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
                  <span className="font-semibold text-foreground">{t("review.table")} {ti + 1}</span>
                  <span className="flex items-center gap-1.5 rounded-full bg-muted px-2.5 py-1 text-xs">
                    {table.extraction_method === "ocr" ? <ScanText className="h-3.5 w-3.5" /> : <Type className="h-3.5 w-3.5" />}
                    {table.extraction_method === "ocr" ? t("review.ocr") : t("review.native")}
                  </span>
                  <span className="rounded-full bg-muted px-2.5 py-1 text-xs">
                    {(table.source_pages && table.source_pages.length > 1)
                      ? `${t("review.pages")}: ${table.source_pages.join(", ")}`
                      : `${t("review.page")}: ${table.pagina_origen}`}
                  </span>
                </div>
                <ConfidenceGrid table={table} onCellSave={handleCellSave} onlyDoubtful={onlyDoubtful} onColumnTypeChange={handleColumnTypeChange} pdf={pdf} />
              </div>
            ))}
          </div>
        )}

        {/* Export + validate panel */}
        {tables.length > 0 && (
          <div className="mt-10 rounded-2xl border border-border bg-card p-6 fade-up">
            <div className="flex flex-wrap items-end justify-between gap-6">
              <div>
                <h2 className="text-lg font-semibold">{t("exportPanel.title")}</h2>
                <p className="mt-1 text-sm text-muted-foreground">{t("exportPanel.subtitle")}</p>
              </div>
              <button
                data-testid="validate-button"
                onClick={validate}
                disabled={doc.estado === "validado" || doc.estado === "exportado"}
                className="flex items-center gap-2 rounded-full border border-emerald-500/40 px-4 py-2.5 text-sm font-semibold text-emerald-500 transition hover:bg-emerald-500/10 disabled:opacity-50"
              >
                <CheckCircle2 className="h-4 w-4" /> {doc.estado === "validado" || doc.estado === "exportado" ? t("review.validated") : t("review.validate")}
              </button>
            </div>
            <div className="mt-5 flex flex-wrap gap-3">
              {exportFmts.map(({ fmt, label, icon: Icon }) => (
                <button
                  key={fmt}
                  data-testid={`export-${fmt}-button`}
                  onClick={() => download(fmt)}
                  disabled={downloading !== null}
                  className="flex items-center gap-2 rounded-xl bg-primary px-5 py-3 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition hover:opacity-95 active:scale-[0.98] disabled:opacity-60"
                >
                  {downloading === fmt ? <Loader2 className="h-4 w-4 animate-spin" /> : <Icon className="h-4 w-4" />}
                  {label}
                </button>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

const Legend = ({ t }) => (
  <div className="flex items-center gap-3 text-xs">
    {[
      { cls: "conf-green", label: t("review.high") },
      { cls: "conf-amber", label: t("review.medium") },
      { cls: "conf-red", label: t("review.low") },
    ].map((x) => (
      <span key={x.cls} className="flex items-center gap-1.5">
        <span className={`h-3 w-3 rounded-sm border ${x.cls}`} />
        <span className="text-muted-foreground">{x.label}</span>
      </span>
    ))}
  </div>
);

export const StatusBadge = ({ estado, t }) => {
  const map = {
    pendiente: "bg-amber-500/15 text-amber-500 border-amber-500/30",
    validado: "bg-emerald-500/15 text-emerald-500 border-emerald-500/30",
    exportado: "bg-primary/15 text-primary border-primary/30",
  };
  return (
    <span data-testid={`status-badge-${estado}`} className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${map[estado] || map.pendiente}`}>
      {t(`history.${estado}`)}
    </span>
  );
};
