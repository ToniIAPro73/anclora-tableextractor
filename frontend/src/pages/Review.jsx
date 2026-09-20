import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useParams, useNavigate } from "react-router-dom";
import {
  FileSpreadsheet, Filter, CheckCircle2, Download, Loader2,
  FileJson, FileText, Sheet, Layers, ScanText, Type, FileStack, Undo2, Redo2, Keyboard,
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
  const [undoStack, setUndoStack] = useState([]);
  const [redoStack, setRedoStack] = useState([]);
  const [reprocessing, setReprocessing] = useState(false);

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

  // ---- low-level appliers (used by actions + undo/redo) ----
  const applyCellState = useCallback(async (tableId, cell) => {
    await api.put(`/documents/${docId}/cell-state`, {
      table_id: tableId, fila: cell.fila, columna: cell.columna,
      valor: cell.valor, score_confianza: cell.score_confianza,
      edited: cell.edited, norm_conf: cell.norm_conf, reason_code: cell.reason_code,
    });
    setTables((prev) => prev.map((tb) =>
      tb.id !== tableId ? tb : {
        ...tb,
        cells: tb.cells.map((c) => (c.fila === cell.fila && c.columna === cell.columna ? { ...c, ...cell } : c)),
      }
    ));
  }, [docId]);

  const applyColumnType = useCallback(async (tableId, columna, tipo) => {
    const res = await api.put(`/documents/${docId}/column-type`, { table_id: tableId, columna, tipo });
    const byId = {};
    res.data.cells.forEach((c) => { byId[`${c.fila}-${c.columna}`] = c; });
    setTables((prev) => prev.map((tb) =>
      tb.id !== tableId ? tb : {
        ...tb,
        column_types: res.data.column_types,
        cells: tb.cells.map((c) => (c.columna === columna ? (byId[`${c.fila}-${c.columna}`] || c) : c)),
      }
    ));
  }, [docId]);

  const pushAction = (action) => {
    setUndoStack((s) => [...s, action]);
    setRedoStack([]);
  };

  const handleColumnTypeChange = async (tableId, columna, tipo) => {
    const table = tables.find((t) => t.id === tableId);
    const prevType = table?.column_types?.[columna] || "text";
    if (prevType === tipo) return;
    try {
      await applyColumnType(tableId, columna, tipo);
      pushAction({
        undo: () => applyColumnType(tableId, columna, prevType),
        redo: () => applyColumnType(tableId, columna, tipo),
      });
      toast.success(t("toast.typeChanged"));
    } catch (e) {
      toast.error(e?.response?.data?.detail || t("toast.error"));
    }
  };

  const handleCellSave = async (tableId, fila, columna, valor) => {
    const table = tables.find((t) => t.id === tableId);
    const prev = { ...table.cells.find((c) => c.fila === fila && c.columna === columna) };
    if (prev.valor === valor) return;
    const next = { ...prev, valor, score_confianza: 1.0, edited: true, norm_conf: 1.0, reason_code: "high" };
    try {
      await applyCellState(tableId, next);
      pushAction({
        undo: () => applyCellState(tableId, prev),
        redo: () => applyCellState(tableId, next),
      });
      toast.success(t("toast.cellSaved"));
    } catch (e) {
      toast.error(t("toast.error"));
    }
  };

  const doUndo = useCallback(async () => {
    setUndoStack((stack) => {
      if (stack.length === 0) return stack;
      const action = stack[stack.length - 1];
      action.undo().catch(() => toast.error(t("toast.error")));
      setRedoStack((r) => [...r, action]);
      return stack.slice(0, -1);
    });
  }, [t]);

  const doRedo = useCallback(async () => {
    setRedoStack((stack) => {
      if (stack.length === 0) return stack;
      const action = stack[stack.length - 1];
      action.redo().catch(() => toast.error(t("toast.error")));
      setUndoStack((u) => [...u, action]);
      return stack.slice(0, -1);
    });
  }, [t]);

  useEffect(() => {
    const onKey = (e) => {
      const mod = e.ctrlKey || e.metaKey;
      if (!mod) return;
      const k = e.key.toLowerCase();
      if (k === "z" && !e.shiftKey) { e.preventDefault(); doUndo(); }
      else if ((k === "z" && e.shiftKey) || k === "y") { e.preventDefault(); doRedo(); }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [doUndo, doRedo]);

  const reprocessOcr = async () => {
    setReprocessing(true);
    try {
      await api.post(`/documents/${docId}/reprocess?mode=ocr&lang=${lang}`);
      setUndoStack([]); setRedoStack([]);
      await load();
      toast.success(t("toast.reprocessed"));
    } catch (e) {
      toast.error(e?.response?.data?.detail || t("toast.error"));
    } finally {
      setReprocessing(false);
    }
  };

  const metrics = useMemo(() => {
    let g = 0, a = 0, r = 0;
    tables.forEach((tb) => tb.cells.forEach((c) => {
      const s = c.score_confianza;
      if (s >= 0.9) g++; else if (s >= 0.6) a++; else r++;
    }));
    const total = g + a + r;
    const pct = (n) => (total ? Math.round((n / total) * 100) : 0);
    return { g, a, r, total, doubtful: a + r, pg: pct(g), pa: pct(a), pr: pct(r) };
  }, [tables]);

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
          <button
            data-testid="reprocess-ocr-button"
            onClick={reprocessOcr}
            disabled={reprocessing}
            title={t("review.reprocessHint")}
            className="flex items-center gap-2 rounded-full border border-border px-4 py-2 text-sm font-semibold text-muted-foreground transition hover:border-primary/50 hover:text-foreground disabled:opacity-60"
          >
            {reprocessing ? <Loader2 className="h-4 w-4 animate-spin" /> : <ScanText className="h-4 w-4" />}
            {t("review.reprocessOcr")}
          </button>
        </div>

        {/* Metrics panel */}
        {metrics.total > 0 && (
          <div data-testid="metrics-panel" className="mt-6 rounded-2xl border border-border bg-card p-5 fade-up">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <h2 className="flex items-center gap-2 text-sm font-semibold text-muted-foreground">
                <Layers className="h-4 w-4" /> {t("review.metricsTitle")}
                <span className="font-mono text-foreground">· {metrics.total} {t("review.cells")}</span>
              </h2>
              <div className="flex items-center gap-4 text-sm">
                <MetricStat testid="metric-green" cls="conf-green" pct={metrics.pg} n={metrics.g} label={t("review.high")} />
                <MetricStat testid="metric-amber" cls="conf-amber" pct={metrics.pa} n={metrics.a} label={t("review.medium")} />
                <MetricStat testid="metric-red" cls="conf-red" pct={metrics.pr} n={metrics.r} label={t("review.low")} />
              </div>
            </div>
            <div className="mt-4 flex h-2.5 w-full overflow-hidden rounded-full bg-muted">
              <div className="bg-emerald-500" style={{ width: `${metrics.pg}%` }} />
              <div className="bg-amber-500" style={{ width: `${metrics.pa}%` }} />
              <div className="bg-red-500" style={{ width: `${metrics.pr}%` }} />
            </div>
            <p className="mt-3 text-xs text-muted-foreground" data-testid="metric-remaining">
              {metrics.doubtful > 0
                ? `${metrics.doubtful} ${t("review.doubtfulLeft")}`
                : t("review.allValidated")}
            </p>
          </div>
        )}

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
            <div className="flex items-center gap-1 rounded-full border border-border p-0.5">
              <button
                data-testid="undo-button"
                onClick={doUndo}
                disabled={undoStack.length === 0}
                title="Ctrl+Z"
                className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium text-muted-foreground transition hover:text-foreground disabled:opacity-40"
              >
                <Undo2 className="h-4 w-4" /> {t("review.undo")}
              </button>
              <button
                data-testid="redo-button"
                onClick={doRedo}
                disabled={redoStack.length === 0}
                title="Ctrl+Shift+Z"
                className="flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium text-muted-foreground transition hover:text-foreground disabled:opacity-40"
              >
                <Redo2 className="h-4 w-4" /> {t("review.redo")}
              </button>
            </div>
            <span data-testid="doubtful-counter" className="text-sm">
              {doubtful > 0 ? (
                <span className="font-semibold text-amber-500">{doubtful} {t("review.doubtfulLeft")}</span>
              ) : (
                <span className="flex items-center gap-1.5 font-semibold text-emerald-500"><CheckCircle2 className="h-4 w-4" /> {t("review.allValidated")}</span>
              )}
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="hidden items-center gap-1.5 text-xs text-muted-foreground lg:flex">
              <Keyboard className="h-3.5 w-3.5" /> {t("review.keyboardHint")}
            </span>
            <Legend t={t} />
          </div>
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

const MetricStat = ({ testid, cls, pct, n, label }) => (
  <div data-testid={testid} className="flex items-center gap-2" title={label}>
    <span className={`h-3 w-3 rounded-sm border ${cls}`} />
    <span className="font-mono font-semibold">{pct}%</span>
    <span className="text-xs text-muted-foreground">({n})</span>
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
