from decimal import Decimal
import textwrap


def _pdf_escape(value):
    text = str(value or "")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _money(value):
    if value is None:
        return "0.00"
    if isinstance(value, Decimal):
        return f"{value:.2f}"
    return f"{Decimal(value):.2f}"


def _wrap_line(line, width=100):
    wrapped = textwrap.wrap(str(line or ""), width=width) or [""]
    return wrapped


def _quote_lines(quote):
    lines = []
    quote_code = quote.code or f"Q-{quote.id}"
    customer_name = quote.customer.name if quote.customer else "-"
    project_name = quote.project.name if quote.project else "-"
    issue_date = quote.issue_date.strftime("%d/%m/%Y") if quote.issue_date else "-"
    valid_until = quote.valid_until.strftime("%d/%m/%Y") if quote.valid_until else "-"
    currency = quote.currency.code if quote.currency_id else "EUR"
    vat = (
        f"{quote.vat_code.code} ({quote.vat_code.rate}%)"
        if quote.vat_code_id
        else "Nessuna / Esente"
    )
    payment = quote.payment_method.name if quote.payment_method_id else "-"
    shipping = quote.shipping_method.name if quote.shipping_method_id else "-"

    lines.extend(
        [
            f"Preventivo {quote_code}",
            "=" * 108,
            f"Titolo: {quote.title}",
            f"Cliente: {customer_name}",
            f"Progetto: {project_name}",
            f"Data emissione: {issue_date}",
            f"Valido fino al: {valid_until}",
            f"Stato: {quote.get_status_display()}",
            f"IVA: {vat}",
            f"Modalita pagamento: {payment}",
            f"Modalita spedizione: {shipping}",
            "",
            "Destinazione merce",
            "-" * 108,
        ]
    )
    delivery = quote.delivery_address
    if delivery:
        lines.append(f"Etichetta: {delivery.label}")
        if delivery.recipient_name:
            lines.append(f"Destinatario: {delivery.recipient_name}")
        lines.append(f"Indirizzo: {delivery.line1}")
        if delivery.line2:
            lines.append(f"Indirizzo 2: {delivery.line2}")
        city_parts = [part for part in [delivery.postal_code, delivery.city, delivery.province] if part]
        if city_parts:
            lines.append(f"Localita: {' '.join(city_parts)}")
        if delivery.country:
            lines.append(f"Nazione: {delivery.country}")
        if delivery.notes:
            lines.append(f"Note consegna: {delivery.notes}")
    else:
        lines.append("Nessuna destinazione merce selezionata.")

    lines.extend(
        [
            "",
            "Righe articolo",
            "-" * 108,
        ]
    )

    quote_rows = quote.lines.order_by("row_order", "id")
    if not quote_rows.exists():
        lines.append("Nessuna riga articolo.")
    else:
        for idx, row in enumerate(quote_rows, start=1):
            row_title = f"{idx}. {row.code} - {row.description}"
            row_detail = (
                f"   Qta {row.quantity} x Netto { _money(row.net_amount) }"
                f" - Sconto {row.discount}% = Totale { _money(row.net_total) } {currency}"
            )
            lines.extend(_wrap_line(row_title, width=106))
            lines.extend(_wrap_line(row_detail, width=106))

    lines.extend(
        [
            "",
            "-" * 108,
            f"Totale netto: {_money(quote.amount_net)} {currency}",
            f"Imposta: {_money(quote.tax_amount)} {currency}",
            f"Totale documento: {_money(quote.total_amount)} {currency}",
        ]
    )

    if quote.note:
        lines.extend(["", "Note", "-" * 108])
        for row in quote.note.splitlines():
            lines.extend(_wrap_line(row, width=106))

    lines.extend(["", "Conferma cliente", "-" * 108])
    if quote.customer_signed_at:
        signed_at = quote.customer_signed_at.strftime("%d/%m/%Y %H:%M")
        lines.append(f"Firmato da: {quote.customer_signed_name or '-'} il {signed_at}")
    else:
        lines.append("Non ancora confermato dal cliente.")

    return lines


def _page_stream(lines):
    commands = ["BT", "/F1 10 Tf", "48 800 Td", "13 TL"]
    first = True
    for line in lines:
        safe = _pdf_escape(line)
        if first:
            commands.append(f"({safe}) Tj")
            first = False
        else:
            commands.append("T*")
            commands.append(f"({safe}) Tj")
    commands.append("ET")
    return "\n".join(commands).encode("latin-1", errors="replace")


def build_quote_pdf_bytes(quote):
    lines = _quote_lines(quote)
    max_lines_per_page = 56
    pages = [lines[idx : idx + max_lines_per_page] for idx in range(0, len(lines), max_lines_per_page)]
    if not pages:
        pages = [["Preventivo"]]

    # Object map:
    # 1 Catalog
    # 2 Pages
    # 3 Font
    # 4..N page/content pairs
    objects = []
    total_pages = len(pages)
    page_ids = []
    content_ids = []

    next_obj_id = 4
    for _ in range(total_pages):
        page_ids.append(next_obj_id)
        content_ids.append(next_obj_id + 1)
        next_obj_id += 2

    catalog_obj = b"<< /Type /Catalog /Pages 2 0 R >>"
    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    pages_obj = f"<< /Type /Pages /Count {total_pages} /Kids [ {kids} ] >>".encode()
    font_obj = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"

    objects.append(catalog_obj)
    objects.append(pages_obj)
    objects.append(font_obj)

    for page_id, content_id, page_lines in zip(page_ids, content_ids, pages):
        stream = _page_stream(page_lines)
        page_obj = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_id} 0 R >>"
        ).encode()
        content_obj = (
            f"<< /Length {len(stream)} >>\nstream\n".encode()
            + stream
            + b"\nendstream"
        )
        objects.append(page_obj)
        objects.append(content_obj)

    pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    for obj_id, payload in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{obj_id} 0 obj\n".encode() + payload + b"\nendobj\n"

    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode()

    trailer = f"<< /Size {len(objects) + 1} /Root 1 0 R >>"
    pdf += b"trailer\n" + trailer.encode() + b"\n"
    pdf += f"startxref\n{xref_start}\n%%EOF\n".encode()
    return pdf
