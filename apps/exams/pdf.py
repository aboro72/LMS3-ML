from html import unescape

from django.utils.html import strip_tags
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def generiere_pruefungsbogen_pdf(pruefung, fragen, mit_loesungen=False):
    from io import BytesIO

    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
        title=f"Prüfungsbogen - {pruefung.titel}",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ExamTitle", parent=styles["Title"], textColor=colors.HexColor("#17365D"), fontSize=18, spaceAfter=6)
    subtitle = ParagraphStyle("ExamSubtitle", parent=styles["BodyText"], textColor=colors.HexColor("#475569"), fontSize=11, spaceAfter=6)
    question = ParagraphStyle("Question", parent=styles["BodyText"], fontSize=11, leading=15, spaceBefore=10, spaceAfter=5)
    answer = ParagraphStyle("Answer", parent=styles["BodyText"], fontSize=10, leading=14, leftIndent=12, spaceAfter=3)
    solution = ParagraphStyle("Solution", parent=answer, textColor=colors.HexColor("#146C43"))
    story = [Paragraph(pruefung.titel, title)]
    story.append(Paragraph("Trainerfassung mit Lösungen" if mit_loesungen else "Teilnehmerfassung ohne Lösungen", subtitle))
    story.append(Paragraph(f"Fragen: {len(fragen)} | Bestehensgrenze: {pruefung.bestehensgrenze_prozent}%", styles["BodyText"]))
    story.append(Spacer(1, 10))
    for nummer, frage in enumerate(fragen, start=1):
        text = unescape(strip_tags(frage.fragetext.html or ""))
        story.append(Paragraph(f"<b>{nummer}. {text}</b> ({frage.punkte} Punkt{'e' if frage.punkte != 1 else ''})", question))
        if frage.typ in [frage.Typ.SINGLE_CHOICE, frage.Typ.MULTIPLE_CHOICE, frage.Typ.WAHR_FALSCH]:
            for antwort in frage.antworten.all():
                prefix = "[x] " if mit_loesungen and antwort.ist_korrekt else "[ ] "
                style = solution if mit_loesungen and antwort.ist_korrekt else answer
                story.append(Paragraph(prefix + unescape(antwort.antworttext), style))
        elif frage.typ == frage.Typ.ZUORDNUNG:
            for paar in frage.zuordnungen.all():
                right = paar.rechtes_element if mit_loesungen else "____________________________"
                story.append(Paragraph(f"{unescape(paar.linkes_element)} → {unescape(right)}", answer))
        else:
            story.append(Spacer(1, 55))
            if mit_loesungen and frage.erklaerung.html:
                story.append(Paragraph("Lösungshinweis: " + unescape(strip_tags(frage.erklaerung.html)), solution))
        if mit_loesungen and frage.typ in [frage.Typ.FREITEXT, frage.Typ.SZENARIO] and frage.bewertungshinweis.html:
            schema = unescape(strip_tags(frage.bewertungshinweis.html))
            story.append(Paragraph(f"Bewertungsschema (max. {frage.punkte} Punkte): {schema}", solution))
        story.append(Spacer(1, 5))
    document.build(story)
    return buffer.getvalue()
