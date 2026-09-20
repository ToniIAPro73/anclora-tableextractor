import * as pdfjsLib from "pdfjs-dist/build/pdf";
import { api } from "@/lib/api";

pdfjsLib.GlobalWorkerOptions.workerSrc =
  "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";

const readFileBuffer = (file) =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result);
    reader.onerror = reject;
    reader.readAsArrayBuffer(file);
  });

export async function renderThumbnails(file, { maxPages = 12, maxW = 160 } = {}) {
  const buf = await readFileBuffer(file);
  const pdf = await pdfjsLib.getDocument({ data: buf }).promise;
  const count = Math.min(pdf.numPages, maxPages);
  const thumbs = [];
  for (let i = 1; i <= count; i++) {
    const page = await pdf.getPage(i);
    const base = page.getViewport({ scale: 1 });
    const scale = maxW / base.width;
    const viewport = page.getViewport({ scale });
    const canvas = document.createElement("canvas");
    canvas.width = Math.ceil(viewport.width);
    canvas.height = Math.ceil(viewport.height);
    const ctx = canvas.getContext("2d");
    await page.render({ canvasContext: ctx, viewport }).promise;
    thumbs.push(canvas.toDataURL("image/jpeg", 0.7));
  }
  const total = pdf.numPages;
  pdf.destroy();
  return { numPages: total, thumbs };
}

export async function loadPdfFromDocId(docId) {
  const res = await api.get(`/documents/${docId}/file`, { responseType: "arraybuffer" });
  const data = new Uint8Array(res.data);
  return pdfjsLib.getDocument({ data }).promise;
}

export async function renderCrop(pdf, pageNum, bbox, { scale = 2.5, pad = 6 } = {}) {
  const page = await pdf.getPage(pageNum);
  const viewport = page.getViewport({ scale });
  const full = document.createElement("canvas");
  full.width = Math.ceil(viewport.width);
  full.height = Math.ceil(viewport.height);
  await page.render({ canvasContext: full.getContext("2d"), viewport }).promise;

  const [x0, top, x1, bottom] = bbox;
  const sx = Math.max(0, x0 * scale - pad);
  const sy = Math.max(0, top * scale - pad);
  const sw = Math.min(full.width - sx, (x1 - x0) * scale + pad * 2);
  const sh = Math.min(full.height - sy, (bottom - top) * scale + pad * 2);

  const crop = document.createElement("canvas");
  crop.width = Math.max(1, Math.ceil(sw));
  crop.height = Math.max(1, Math.ceil(sh));
  crop.getContext("2d").drawImage(full, sx, sy, sw, sh, 0, 0, sw, sh);
  return crop.toDataURL("image/jpeg", 0.85);
}
