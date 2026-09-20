import React, { useState, useRef, useEffect } from "react";
import { Pencil } from "lucide-react";

export const confClass = (score) => {
  if (score >= 0.9) return "conf-green";
  if (score >= 0.6) return "conf-amber";
  return "conf-red";
};

const cellAt = (table, r, c) =>
  table.cells.find((x) => x.fila === r && x.columna === c) || null;

export const ConfidenceGrid = ({ table, onCellSave, onlyDoubtful }) => {
  const [editing, setEditing] = useState(null); // {r, c}
  const [draft, setDraft] = useState("");
  const inputRef = useRef(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const startEdit = (r, c, value) => {
    setEditing({ r, c });
    setDraft(value ?? "");
  };

  const commit = async () => {
    if (!editing) return;
    const { r, c } = editing;
    const current = cellAt(table, r, c);
    if (current && draft !== current.valor) {
      await onCellSave(table.id, r, c, draft);
    }
    setEditing(null);
  };

  const onKeyDown = (e) => {
    if (e.key === "Enter") { e.preventDefault(); commit(); }
    else if (e.key === "Escape") { e.preventDefault(); setEditing(null); }
  };

  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-card thin-scroll">
      <table data-testid={`grid-table-${table.id}`} className="w-full border-collapse text-sm">
        <thead>
          <tr className="bg-muted/60">
            <th className="sticky left-0 z-10 border-b border-r border-border bg-muted/80 px-3 py-2 text-left text-xs font-semibold text-muted-foreground">#</th>
            {table.columnas.map((col, ci) => (
              <th key={ci} className="border-b border-border px-3 py-2 text-left text-xs font-bold uppercase tracking-wide text-foreground/80 whitespace-nowrap">
                {col}
                {table.column_types?.[ci] && (
                  <span className="ml-1.5 font-mono text-[10px] font-normal text-primary/70">{table.column_types[ci]}</span>
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {Array.from({ length: table.num_filas }).map((_, r) => (
            <tr key={r} className="hover:bg-muted/30">
              <td className="sticky left-0 z-10 border-r border-border bg-card px-3 py-1.5 text-xs font-medium text-muted-foreground">{r + 1}</td>
              {table.columnas.map((_, c) => {
                const cell = cellAt(table, r, c);
                const score = cell ? cell.score_confianza : 1;
                const isDoubtful = score < 0.9;
                const isEditing = editing && editing.r === r && editing.c === c;
                const dim = onlyDoubtful && !isDoubtful;
                return (
                  <td
                    key={c}
                    data-testid={`cell-${table.id}-${r}-${c}`}
                    data-score={score}
                    className={`group relative border border-transparent px-0 py-0 align-middle data-cell ${confClass(score)} ${dim ? "conf-dimmed" : ""}`}
                    onClick={() => !isEditing && !dim && startEdit(r, c, cell?.valor)}
                  >
                    {isEditing ? (
                      <input
                        ref={inputRef}
                        data-testid={`cell-input-${table.id}-${r}-${c}`}
                        value={draft}
                        onChange={(e) => setDraft(e.target.value)}
                        onBlur={commit}
                        onKeyDown={onKeyDown}
                        className="w-full min-w-[7rem] bg-background px-3 py-1.5 text-sm outline-none ring-2 ring-primary"
                      />
                    ) : (
                      <div className="flex min-w-[7rem] cursor-text items-center justify-between gap-2 px-3 py-1.5">
                        <span className="truncate">{cell?.valor}</span>
                        <span className="flex items-center gap-1">
                          {cell?.edited && <span className="h-1.5 w-1.5 rounded-full bg-primary" title="editado" />}
                          {isDoubtful && !dim && (
                            <Pencil className="h-3 w-3 opacity-0 transition group-hover:opacity-70" />
                          )}
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
