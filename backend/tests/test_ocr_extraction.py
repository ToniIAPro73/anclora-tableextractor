from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from extraction import extract_tables


def _image_only_pdf(path: Path) -> None:
    image = Image.new("RGB", (1600, 2000), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 64)
        bold = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 68)
    except OSError:
        font = bold = ImageFont.load_default()

    columns = [(100, 520), (600, 600), (1250, 300)]
    rows = [
        ("Fecha", "Concepto", "Importe"),
        ("01/09/2026", "QA item A", "123.45"),
        ("02/09/2026", "QA item B", "678.90"),
        ("03/09/2026", "QA item C", "42.00"),
    ]
    top, row_height = 350, 190
    for row_index, row in enumerate(rows):
        y = top + row_index * row_height
        for column_index, value in enumerate(row):
            x, width = columns[column_index]
            draw.rectangle((x, y, x + width, y + row_height), outline="black", width=6)
            draw.text((x + 18, y + 48), value, fill="black", font=bold if row_index == 0 else font)

    image_path = path.with_suffix(".png")
    image.save(image_path)
    try:
        document = canvas.Canvas(str(path), pagesize=A4)
        document.drawImage(ImageReader(str(image_path)), 0, 0, width=A4[0], height=A4[1])
        document.showPage()
        document.save()
    finally:
        image_path.unlink(missing_ok=True)


def test_image_only_pdf_uses_ocr_and_reconstructs_table(tmp_path):
    pdf_path = tmp_path / "qa-image-only.pdf"
    _image_only_pdf(pdf_path)

    page_count, tables = extract_tables(str(pdf_path), lang="es")

    assert page_count == 1
    assert tables
    assert all(table["method"] == "ocr" for table in tables)
    assert tables[0]["ncols"] >= 2
    assert len(tables[0]["rows"]) >= 2
    assert sum(bool(cell["value"]) for row in tables[0]["rows"] for cell in row) >= 4
