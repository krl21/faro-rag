"""Build small PDFs in memory for tests (valid, blank/scanned and corrupt)."""


def _escape(text: str) -> str:
    """Escape a string for a PDF literal.

    Args:
        text: Raw text.

    Returns:
        Text with backslashes and parentheses escaped.
    """
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def make_pdf(pages: list[str]) -> bytes:
    """Create a PDF with one text page per entry.

    An empty string produces a page without text, like a scanned page
    without an OCR layer.

    Args:
        pages: Text of each page; lines are separated by ``\\n``.

    Returns:
        The PDF bytes.
    """
    page_ids = [4 + 2 * i for i in range(len(pages))]
    objects: dict[int, bytes] = {
        1: b"<< /Type /Catalog /Pages 2 0 R >>",
        2: (
            f"<< /Type /Pages /Kids [{' '.join(f'{p} 0 R' for p in page_ids)}] "
            f"/Count {len(pages)} >>"
        ).encode(),
        3: b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    }
    for page_id, text in zip(page_ids, pages, strict=True):
        lines = " ".join(f"({_escape(line)}) Tj T*" for line in text.split("\n") if line)
        stream = f"BT /F1 11 Tf 50 780 Td 14 TL {lines} ET".encode("latin-1")
        objects[page_id] = (
            "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {page_id + 1} 0 R >>"
        ).encode()
        objects[page_id + 1] = (
            f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream"
        )

    output = bytearray(b"%PDF-1.4\n")
    offsets: dict[int, int] = {}
    for number in sorted(objects):
        offsets[number] = len(output)
        output += f"{number} 0 obj\n".encode() + objects[number] + b"\nendobj\n"
    xref_start = len(output)
    size = max(objects) + 1
    output += f"xref\n0 {size}\n0000000000 65535 f \n".encode()
    for number in range(1, size):
        output += f"{offsets[number]:010d} 00000 n \n".encode()
    output += f"trailer\n<< /Size {size} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode()
    return bytes(output)


POLICY_TEXT = """Seguros Faro del Sur
Póliza de seguro de automóvil
Número de póliza: FS-2024-001
Tomador: Juan Pérez García
NIF: 12345678Z
Matrícula: 1234-BCD
Vigencia: desde 01/01/2025 hasta 31/12/2025
Coberturas incluidas:
- Responsabilidad civil obligatoria
- Robo total del vehículo
- Asistencia en carretera 24 horas
El asegurado debe comunicar el siniestro en un plazo de siete días."""

INVOICE_TEXT = """Taller Mecánico El Faro
Factura número 2025-0042
Fecha: 15/03/2025
Cliente: Juan Pérez García
Referencia póliza: FS-2024-001
Vehículo matrícula 1234-BCD
Reparación de paragolpes delantero y pintura.
Importe total: 1.250,50 EUR"""

CORRUPT_PDF = b"%PDF-1.4\nthis is not a real pdf structure\n%%EOF"
