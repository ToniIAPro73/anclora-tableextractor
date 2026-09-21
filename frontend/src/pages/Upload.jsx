import React, { useCallback, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { UploadCloud, FileText, X, Loader2, CheckCircle2, AlertCircle, Table2, ArrowRight, Images } from "lucide-react";
import { toast } from "sonner";
import { Header } from "@/components/Header";
import { useLang } from "@/contexts/LangContext";
import { api } from "@/lib/api";
import { renderThumbnails } from "@/lib/pdf";

const fmtSize = (b) => {
  if (b < 1024) return `${b} B`;
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(0)} KB`;
  return `${(b / 1024 / 1024).toFixed(1)} MB`;
};

export default function Upload() {
  const { t, lang } = useLang();
  const navigate = useNavigate();
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [files, setFiles] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [results, setResults] = useState([]);
  const [thumbs, setThumbs] = useState({}); // id -> {loading, numPages, images}

  const addFiles = useCallback((list) => {
    const pdfs = Array.from(list).filter((f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"));
    if (pdfs.length === 0) {
      toast.error(lang === "es" ? "Solo se admiten archivos PDF" : "Only PDF files are supported");
      return;
    }
    const items = pdfs.map((f) => ({ file: f, id: `${f.name}-${f.size}-${Date.now()}-${Math.random()}` }));
    setFiles((prev) => [...prev, ...items]);
    setResults([]);
    items.forEach(async (it) => {
      setThumbs((prev) => ({ ...prev, [it.id]: { loading: true, images: [], numPages: 0 } }));
      try {
        const { numPages, thumbs: imgs } = await renderThumbnails(it.file);
        setThumbs((prev) => ({ ...prev, [it.id]: { loading: false, images: imgs, numPages } }));
      } catch (e) {
        setThumbs((prev) => ({ ...prev, [it.id]: { loading: false, images: [], numPages: 0 } }));
      }
    });
  }, [lang]);

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    addFiles(e.dataTransfer.files);
  };

  const removeFile = (id) => setFiles((prev) => prev.filter((f) => f.id !== id));

  const process = async () => {
    if (files.length === 0) return;
    setProcessing(true);
    setResults([]);
    try {
      const form = new FormData();
      files.forEach((f) => form.append("files", f.file));
      const res = await api.post(`/documents/upload?lang=${lang}`, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResults(res.data.documents);
      setFiles([]);
      toast.success(t("toast.uploaded"));
    } catch (e) {
      toast.error(e?.response?.data?.detail || t("toast.error"));
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <Header />
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="fade-up">
          <h1 className="text-2xl font-bold tracking-tight sm:text-3xl" style={{ fontFamily: "Manrope, sans-serif" }}>
            {t("upload.title")}
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">{t("upload.subtitle")}</p>
        </div>

        {/* Dropzone */}
        <div
          data-testid="upload-dropzone"
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`mt-6 grid-bg flex cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed px-6 py-14 text-center transition-all ${
            dragging ? "border-primary bg-primary/5 scale-[1.01]" : "border-border hover:border-primary/50 hover:bg-muted/40"
          }`}
        >
          <input
            ref={inputRef}
            data-testid="file-input"
            type="file"
            accept="application/pdf"
            multiple
            className="hidden"
            onChange={(e) => addFiles(e.target.files)}
          />
          <span className={`flex h-16 w-16 items-center justify-center rounded-2xl transition ${dragging ? "bg-primary/20" : "bg-primary/10"}`}>
            <UploadCloud className="h-8 w-8 text-primary" strokeWidth={1.6} />
          </span>
          <p className="mt-4 text-base font-semibold">{t("upload.dropzone")}</p>
          <p className="mt-1 text-sm text-muted-foreground">{t("upload.dropzoneHint")}</p>
          <span className="mt-4 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground">
            {t("upload.selectFiles")}
          </span>
        </div>

        {/* Queue */}
        {files.length > 0 && (
          <div className="mt-6 fade-up">
            <div className="mb-3 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-muted-foreground">
                {t("upload.queue")} · {files.length}
              </h2>
              <button
                data-testid="process-button"
                onClick={process}
                disabled={processing}
                className="flex items-center gap-2 rounded-full bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-lg shadow-primary/25 transition hover:opacity-95 active:scale-[0.98] disabled:opacity-60"
              >
                {processing ? <Loader2 className="h-4 w-4 animate-spin" /> : <Table2 className="h-4 w-4" />}
                {processing ? t("upload.processing") : t("upload.process")}
              </button>
            </div>
            <div className="space-y-2">
              {files.map((f) => {
                const th = thumbs[f.id] || { loading: true, images: [], numPages: 0 };
                return (
                <div key={f.id} data-testid="queue-item" className="rounded-xl border border-border bg-card px-4 py-3">
                  <div className="flex items-center gap-3">
                    <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/10">
                      <FileText className="h-5 w-5 text-red-500" strokeWidth={1.7} />
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{f.file.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {fmtSize(f.file.size)}
                        {th.numPages > 0 && ` · ${th.numPages} ${t("upload.pages")}`}
                      </p>
                    </div>
                    {!processing && (
                      <button data-testid="remove-file-button" onClick={() => removeFile(f.id)} className="rounded-lg p-2 text-muted-foreground hover:bg-muted hover:text-destructive">
                        <X className="h-4 w-4" />
                      </button>
                    )}
                    {processing && <Loader2 className="h-4 w-4 animate-spin text-primary" />}
                  </div>

                  {/* Page thumbnails */}
                  <div className="mt-3 flex items-center gap-2 border-t border-border pt-3">
                    <Images className="h-4 w-4 shrink-0 text-muted-foreground" />
                    {th.loading ? (
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Loader2 className="h-3.5 w-3.5 animate-spin" /> {t("upload.preview")}…
                      </div>
                    ) : th.images.length === 0 ? (
                      <span className="text-xs text-muted-foreground">{t("upload.preview")}: —</span>
                    ) : (
                      <div className="flex gap-2 overflow-x-auto thin-scroll" data-testid={`thumbs-${f.id}`}>
                        {th.images.map((src, pi) => (
                          <div key={pi} className="group relative shrink-0">
                            <img
                              src={src}
                              alt={`p${pi + 1}`}
                              className="h-24 w-auto rounded-md border border-border bg-white shadow-sm transition group-hover:ring-2 group-hover:ring-primary"
                            />
                            <span className="absolute bottom-1 left-1 rounded bg-black/70 px-1.5 py-0.5 text-[10px] font-medium text-white">
                              {t("upload.page")} {pi + 1}
                            </span>
                          </div>
                        ))}
                        {th.numPages > th.images.length && (
                          <div className="flex h-24 shrink-0 items-center rounded-md border border-dashed border-border px-3 text-xs text-muted-foreground">
                            +{th.numPages - th.images.length} {t("upload.morePages")}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Results */}
        {results.length > 0 && (
          <div className="mt-8 fade-up">
            <h2 className="mb-3 text-sm font-semibold text-muted-foreground">{t("upload.done")}</h2>
            <div className="space-y-2">
              {results.map((r) => (
                <div key={r.id || r.nombre_archivo} data-testid="result-item" className="flex items-center gap-3 rounded-xl border border-border bg-card px-4 py-3">
                  {r.error ? (
                    <AlertCircle className="h-5 w-5 shrink-0 text-destructive" />
                  ) : (
                    <CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-500" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{r.nombre_archivo}</p>
                    {r.error ? (
                      <p className="text-xs text-destructive">{r.error}</p>
                    ) : (
                      <p className="text-xs text-muted-foreground">
                        {r.num_paginas} {t("upload.pages")} · {r.num_tablas} {t("upload.tables")} · {t("upload.processedIn")} {(r.process_ms / 1000).toFixed(1)}s
                      </p>
                    )}
                  </div>
                  {!r.error && (
                    <button
                      data-testid="review-result-button"
                      onClick={() => navigate(`/review/${r.id}`)}
                      className="flex items-center gap-1.5 rounded-full border border-primary/40 px-3 py-1.5 text-xs font-semibold text-primary transition hover:bg-primary/10"
                    >
                      {t("upload.viewResult")} <ArrowRight className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
