import React, { useState, useRef, useEffect } from "react";
import { Pencil, Info, ChevronDown, Calendar, Hash, Type as TypeIcon, Loader2 } from "lucide-react";
import { useLang } from "@/contexts/LangContext";
import { renderCrop } from "@/lib/pdf";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export const confClass = (score) => {
  if (score >= 0.9) return "conf-green";
  if (score >= 0.6) return "conf-amber";
  return "conf-red";
};

const cellAt = (table, r, c) => table.cells.find((x) => x.fila === r && x.columna === c) || null;
const TYPE_ICONS = { date: Calendar, number: Hash, text: TypeIcon };

const CellDetail = ({ cell, method, pdf, t }) => {
  const [crop, setCrop] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tried, setTried] = useState(false);
  const pct = (v) => `${Math.round((v ?? 0) * 100)}%`;

  const onOpen = async (open) => {
    if (!open || tried || !pdf || !cell.bbox) return;
    setTried(true);
    setLoading(true);
    try {
      setCrop(await renderCrop(pdf, cell.pagina, cell.bbox));
    } catch (e) { /* noop */ } finally { setLoading(false); }
  };

  return (
    <Popover onOpenChange={onOpen}>
      <PopoverTrigger asChild>
        <button
          data-testid={`cell-detail-button-${cell.fila}-${cell.columna}`}
          className="rounded p-0.5 text-current opacity-60 transition hover:opacity-100"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
          title={t("review.detailTitle")}
          tabIndex={-1}
        >
          <Info className="h-3.5 w-3.5" />
        </button>
      </PopoverTrigger>
      <PopoverContent align="start" className="w-72" data-testid="cell-detail-popover">
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <span className={`h-2.5 w-2.5 rounded-full ${confClass(cell.score_confianza)}`} />
            <h4 className="text-sm font-semibold">{t("review.detailTitle")}</h4>
          </div>
          <p className="text-xs text-muted-foreground">{t(`review.reasons.${cell.reason_code || "high"}`)}</p>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <Stat label={t("review.score")} value={pct(cell.score_confianza)} />
            <Stat label={t("review.page")} value={cell.pagina} />
            <Stat label={t("review.extractionConf")} value={pct(cell.extraction_conf)} />
            <Stat label={t("review.normConf")} value={pct(cell.norm_conf)} />
            <Stat label={t("review.method")} value={method === "ocr" ? "OCR" : t("review.native")} />
            <Stat label={t("review.original")} value={cell.valor_original || "—"} mono />
          </div>
          <div>
            <p className="mb-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{t("review.cropLabel")}</p>
            {loading ? (
              <div className="flex h-16 items-center justify-center rounded-md border border-border bg-muted/40"><Loader2 className="h-4 w-4 animate-spin text-primary" /></div>
            ) : crop ? (
              <img src={crop} alt="crop" data-testid="cell-crop-image" className="max-h-28 w-full rounded-md border border-border bg-white object-contain" />
            ) : (
              <div className="flex h-14 items-center justify-center rounded-md border border-dashed border-border text-[11px] text-muted-foreground">{t("review.noCrop")}</div>
            )}
          </div>
        </div>
      </PopoverContent>
    </Popover>
  );
};

const Stat = ({ label, value, mono }) => (
  <div className="rounded-md bg-muted/50 px-2 py-1.5">
    <p className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</p>
    <p className={`truncate text-xs font-semibold ${mono ? "font-mono" : ""}`}>{value}</p>
  </div>
);

const ColumnTypeMenu = ({ table, colIdx, onColumnTypeChange, t }) => {
  const current = table.column_types?.[colIdx] || "text";
  const opts = [
    { key: "date", label: t("review.typeDate"), icon: Calendar },
    { key: "number", label: t("review.typeNumber"), icon: Hash },
    { key: "text", label: t("review.typeText"), icon: TypeIcon },
  ];
  const CurIcon = TYPE_ICONS[current] || TypeIcon;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          data-testid={`column-type-button-${table.id}-${colIdx}`}
          onClick={(e) => e.stopPropagation()}
          className="ml-1.5 inline-flex items-center gap-1 rounded-md bg-primary/10 px-1.5 py-0.5 font-mono text-[10px] font-normal text-primary/80 transition hover:bg-primary/20"
          title={t("review.changeType")}
        >
          <CurIcon className="h-3 w-3" /> {current}
          <ChevronDown className="h-3 w-3" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {opts.map((o) => {
          const Icon = o.icon;
          return (
            <DropdownMenuItem
              key={o.key}
              data-testid={`column-type-option-${table.id}-${colIdx}-${o.key}`}
              onClick={() => o.key !== current && onColumnTypeChange(table.id, colIdx, o.key)}
              className={`gap-2 cursor-pointer ${o.key === current ? "text-primary font-semibold" : ""}`}
            >
              <Icon className="h-4 w-4" /> {o.label}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
};

export const ConfidenceGrid = ({ table, onCellSave, onlyDoubtful, onColumnTypeChange, pdf }) => {
  const { t } = useLang();
  const nrows = table.num_filas;
  const ncols = table.num_columnas;
  const [sel, setSel] = useState(null); // {r,c}
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState("");
  const inputRef = useRef(null);
  const cellRefs = useRef({});
  const selR = sel ? sel.r : -1;
  const selC = sel ? sel.c : -1;

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing, selR, selC]);

  const isDim = (r, c) => {
    const cell = cellAt(table, r, c);
    const score = cell ? cell.score_confianza : 1;
    return onlyDoubtful && score >= 0.9;
  };

  const focusTd = (r, c) => {
    requestAnimationFrame(() => cellRefs.current[`${r}-${c}`]?.focus());
  };

  const selectCell = (r, c) => {
    if (r < 0 || c < 0 || r >= nrows || c >= ncols) return;
    setEditing(false);
    setSel({ r, c });
    focusTd(r, c);
  };

  const beginEdit = (r, c, initial) => {
    if (r < 0 || c < 0 || r >= nrows || c >= ncols || isDim(r, c)) return;
    const cell = cellAt(table, r, c);
    setSel({ r, c });
    setDraft(initial != null ? initial : (cell?.valor ?? ""));
    setEditing(true);
  };

  const commit = async () => {
    if (!editing || !sel) return;
    const { r, c } = sel;
    const cur = cellAt(table, r, c);
    if (cur && draft !== cur.valor) await onCellSave(table.id, r, c, draft);
    setEditing(false);
  };

  const nextCell = (r, c, back) => {
    let nr = r, nc = c + (back ? -1 : 1);
    if (nc >= ncols) { nc = 0; nr = r + 1; }
    if (nc < 0) { nc = ncols - 1; nr = r - 1; }
    return { nr, nc };
  };

  const commitThenTarget = async (nr, nc, edit) => {
    await commit();
    if (nr < 0 || nc < 0 || nr >= nrows || nc >= ncols) {
      selectCell(sel.r, sel.c);
      return;
    }
    if (edit && !isDim(nr, nc)) beginEdit(nr, nc);
    else selectCell(nr, nc);
  };

  const onTdKeyDown = (e, r, c) => {
    if (editing) return;
    if (e.key === "ArrowUp") { e.preventDefault(); selectCell(r - 1, c); }
    else if (e.key === "ArrowDown") { e.preventDefault(); selectCell(r + 1, c); }
    else if (e.key === "ArrowLeft") { e.preventDefault(); selectCell(r, c - 1); }
    else if (e.key === "ArrowRight") { e.preventDefault(); selectCell(r, c + 1); }
    else if (e.key === "Tab") { e.preventDefault(); const { nr, nc } = nextCell(r, c, e.shiftKey); selectCell(nr, nc); }
    else if (e.key === "Enter" || e.key === "F2") { e.preventDefault(); beginEdit(r, c); }
    else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) { e.preventDefault(); beginEdit(r, c, e.key); }
  };

  const onInputKeyDown = async (e) => {
    if (e.key === "Enter") { e.preventDefault(); await commitThenTarget(sel.r + 1, sel.c, true); }
    else if (e.key === "Tab") { e.preventDefault(); const { nr, nc } = nextCell(sel.r, sel.c, e.shiftKey); await commitThenTarget(nr, nc, true); }
    else if (e.key === "Escape") { e.preventDefault(); setEditing(false); focusTd(sel.r, sel.c); }
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card thin-scroll">
      <table data-testid={`grid-table-${table.id}`} className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-muted/60">
            <th className="sticky left-0 z-10 border-b border-r border-border bg-muted/80 px-3 py-2 text-left text-xs font-semibold text-muted-foreground">#</th>
            {table.columnas.map((col, ci) => (
              <th key={ci} className="border-b border-border px-3 py-2 text-left text-xs font-bold uppercase tracking-wide text-foreground/80 whitespace-nowrap">
                <span className="inline-flex items-center">
                  {col}
                  <ColumnTypeMenu table={table} colIdx={ci} onColumnTypeChange={onColumnTypeChange} t={t} />
                </span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: nrows }).map((_, r) => (
            <tr key={r} className="hover:bg-muted/30">
              <td className="sticky left-0 z-10 border-r border-border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground">{r + 1}</td>
              {table.columnas.map((_, c) => {
                const cell = cellAt(table, r, c);
                const score = cell ? cell.score_confianza : 1;
                const isDoubtful = score < 0.9;
                const isEditing = editing && sel && sel.r === r && sel.c === c;
                const isSel = sel && sel.r === r && sel.c === c;
                const dim = onlyDoubtful && !isDoubtful;
                return (
                  <td
                    key={c}
                    ref={(el) => (cellRefs.current[`${r}-${c}`] = el)}
                    data-testid={`cell-${table.id}-${r}-${c}`}
                    data-score={score}
                    tabIndex={dim ? -1 : 0}
                    className={`group relative border align-middle outline-none data-cell ${confClass(score)} ${dim ? "conf-dimmed" : ""} ${isSel && !isEditing ? "z-20 ring-2 ring-inset ring-primary" : "border-transparent"}`}
                    onClick={() => !isEditing && !dim && selectCell(r, c)}
                    onDoubleClick={() => !dim && beginEdit(r, c)}
                    onFocus={() => { if (!isDim(r, c)) setSel({ r, c }); }}
                    onKeyDown={(e) => onTdKeyDown(e, r, c)}
                  >
                    {isEditing ? (
                      <input
                        ref={inputRef}
                        data-testid={`cell-input-${table.id}-${r}-${c}`}
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        onBlur={commit}
                        onKeyDown={onInputKeyDown}
                        className="w-full min-w-[7rem] bg-background px-3 py-1.5 text-sm outline-none ring-2 ring-primary"
                      />
                    ) : (
                      <div className="flex min-w-[7rem] cursor-text items-center justify-between gap-2 px-3 py-1.5">
                        <span className="truncate">{cell?.valor}</span>
                        <span className="flex items-center gap-1">
                          {cell?.edited && <span className="h-1.5 w-1.5 rounded-full bg-primary" title="editado" />}
                          {isDoubtful && !dim && cell && (
                            <CellDetail cell={cell} method={table.extraction_method} pdf={pdf} t={t} />
                          )}
                          {isDoubtful && !dim && <Pencil className="h-3 w-3 opacity-0 transition group-hover:opacity-70" />}
                        </span>
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};
