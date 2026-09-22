import base64
import io

import qrcode
from django.core.files.base import ContentFile
from django.db import transaction
from django.template.loader import render_to_string


def stelle_zertifikat_aus(pruefungsversuch):
    from .models import InterneZertifikatsnummer, Zertifikat

    if not pruefungsversuch.bestanden:
        return None
    with transaction.atomic():
        zert = Zertifikat.objects.filter(pruefungsversuch=pruefungsversuch).first()
        if zert:
            return zert
        from apps.exams.models import Pruefung
        pruefung = Pruefung.objects.select_for_update().get(pk=pruefungsversuch.pruefung_id)
        if pruefung.zertifikatsnummernart == Pruefung.Zertifikatsnummernart.EXTERN:
            nummer = pruefung.externe_nummern_naechste
            if pruefung.externe_nummern_ende and nummer > pruefung.externe_nummern_ende:
                raise ValueError("Der externe Zertifikatsnummernbereich ist aufgebraucht.")
            pruefung.externe_nummern_naechste = nummer + 1
            pruefung.save(update_fields=["externe_nummern_naechste"])
            zertifikatsnummer = f"{pruefung.externe_nummern_prefix}{nummer}"
        else:
            stand = InterneZertifikatsnummer.objects.select_for_update().get_or_create(pk=1, defaults={"naechste_nummer": 5001})[0]
            zertifikatsnummer = str(stand.naechste_nummer)
            stand.naechste_nummer += 1
            stand.save(update_fields=["naechste_nummer"])
        return Zertifikat.objects.create(nutzer=pruefungsversuch.nutzer, pruefungsversuch=pruefungsversuch, zertifikatsnummer=zertifikatsnummer)


def _generiere_qr_code_b64(url):
    qr = qrcode.QRCode(box_size=4, border=2)
    qr.add_data(url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


def _lade_design(organisation):
    from .models import ZertifikatDesign

    if organisation is None:
        from types import SimpleNamespace
        return SimpleNamespace(
            primary_color="#12315f",
            secondary_color="#f28c28",
            org_display_name="",
            footer_text="",
            signature_line="",
            unterschrift_1=None,
            unterschrift_2=None,
            logo=None,
        )
    design, _ = ZertifikatDesign.objects.get_or_create(organisation=organisation)
    return design


def _bild_b64(bild):
    if not bild:
        return None
    try:
        with open(bild.path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        ext = bild.name.rsplit(".", 1)[-1].lower()
        mime = "image/png" if ext == "png" else "image/jpeg"
        return f"data:{mime};base64,{data}"
    except (FileNotFoundError, AttributeError, ValueError):
        return None


def generiere_zertifikat_pdf(zertifikat, base_url):
    # Lazy import: WeasyPrint benötigt GTK-Systemlibaries (Windows: GTK-Runtime installieren)
    try:
        from weasyprint import HTML
    except OSError as exc:
        raise RuntimeError(
            "WeasyPrint konnte GTK-Bibliotheken nicht laden. "
            "Bitte installiere die GTK3-Runtime fuer Windows: "
            "https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows"
        ) from exc

    org = zertifikat.get_organisation()
    design = _lade_design(org)
    verify_url = f"{base_url.rstrip('/')}/zertifikate/verify/{zertifikat.code}/"
    qr_b64 = _generiere_qr_code_b64(verify_url)
    org_name = design.org_display_name or (org.name if org else "ABoroLMS")
    html_string = render_to_string(
        "certificates/pdf.html",
        {
            "zertifikat": zertifikat,
            "verify_url": verify_url,
            "qr_b64": qr_b64,
            "primary_color": design.primary_color,
            "secondary_color": design.secondary_color,
            "org_name": org_name,
            "footer_text": design.footer_text,
            "signature_line": design.signature_line,
            "logo_b64": _bild_b64(design.logo),
            "unterschrift_1_b64": _bild_b64(design.unterschrift_1),
            "unterschrift_2_b64": _bild_b64(design.unterschrift_2),
        },
    )
    return HTML(string=html_string).write_pdf()


def speichere_zertifikat_pdf(zertifikat, base_url):
    if zertifikat.pdf_datei:
        return zertifikat.pdf_datei
    pdf = generiere_zertifikat_pdf(zertifikat, base_url)
    zertifikat.pdf_datei.save(f"zertifikat-{zertifikat.zertifikatsnummer or zertifikat.code}.pdf", ContentFile(pdf), save=True)
    return zertifikat.pdf_datei
