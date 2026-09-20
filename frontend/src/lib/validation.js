// Client-side evaluation of per-column validation rules.
export function violatesRule(value, rule) {
  if (!rule) return false;
  const v = (value ?? "").toString().trim();
  if (rule.required && v === "") return true;
  const hasRange = rule.min != null || rule.max != null;
  if (hasRange && v !== "") {
    const n = parseFloat(v.replace(/\s/g, "").replace(",", "."));
    if (isNaN(n)) return true;
    if (rule.min != null && n < rule.min) return true;
    if (rule.max != null && n > rule.max) return true;
  }
  return false;
}

// Effective score used for coloring/metrics: a rule violation forces "red".
export function effectiveScore(cell, rule) {
  if (violatesRule(cell.valor, rule)) return Math.min(cell.score_confianza, 0.3);
  return cell.score_confianza;
}

export function ruleOf(table, colIdx) {
  return table.column_rules ? table.column_rules[String(colIdx)] : undefined;
}
