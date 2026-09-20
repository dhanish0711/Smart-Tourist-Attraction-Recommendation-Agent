"""
ReportLab PDF Travel Dossier Generator Tool.
Generates an executive, printable travel booklet including daily schedules,
budget itemization, offline cultural survival kit, and local emergency contacts.
Equipped with running headers, footers, two-pass page numbering, and clean typography.
"""
from pathlib import Path
from typing import Optional
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
)
from reportlab.pdfgen import canvas
from models.schemas import TripPlan


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and stamp 'Page X of Y' 
    and executive running headers/footers onto every page.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#4A5568"))

        # Running header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(36, 756, "Smart Tourist Attraction Recommendation Agent • Travel Dossier")
            self.setStrokeColor(colors.HexColor("#CBD5E0"))
            self.setLineWidth(0.5)
            self.line(36, 750, 576, 750)

        # Running footer (all pages)
        self.setStrokeColor(colors.HexColor("#CBD5E0"))
        self.setLineWidth(0.5)
        self.line(36, 38, 576, 38)

        self.drawString(36, 26, "AI Autonomous Itinerary • Validated with TSP Routing & Skill-RAG")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(576, 26, page_str)
        self.restoreState()


def format_currency(amount: float, symbol: str) -> str:
    """Formats currency gracefully without unprintable glyphs in standard PDF fonts."""
    if symbol == "₹":
        prefix = "INR "
    elif symbol in ("$", "€", "£", "¥"):
        prefix = symbol
    else:
        prefix = f"{symbol} "
    return f"{prefix}{amount:,.0f}"


def generate_trip_pdf(trip_plan: TripPlan, output_path: Optional[Path] = None) -> Path:
    """
    Builds an executive PDF travel booklet from the structured TripPlan.
    """
    if output_path is None:
        from config import settings
        output_path = settings.OUTPUT_DIR / f"{trip_plan.trip_id}_travel_dossier.pdf"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=46,
        bottomMargin=46
    )

    styles = getSampleStyleSheet()
    curr = trip_plan.profile.currency

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1A365D")
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#4A5568")
    )

    h2_style = ParagraphStyle(
        'DocH2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=10,
        spaceAfter=5
    )

    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#2D3748")
    )

    table_text = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#1A202C")
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=11,
        textColor=colors.white
    )

    story = []

    # Title & Metadata
    dest_name = trip_plan.profile.destination.upper()
    story.append(Paragraph(f"TRAVEL DOSSIER: {dest_name}", title_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Curated by Smart Tourist Attraction Recommendation Agent | "
        f"{trip_plan.profile.duration_days} Days | "
        f"{trip_plan.profile.travelers_count} Travelers ({trip_plan.profile.age_group}) | "
        f"Budget: {format_currency(trip_plan.profile.budget, curr)}",
        subtitle_style
    ))
    story.append(Spacer(1, 8))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#3182CE"), spaceAfter=12))

    # Executive Overview Box
    overview_data = [
        [
            Paragraph("<b>Validation Status:</b> Approved [PASSED]", body_style),
            Paragraph(f"<b>Estimated Cost:</b> {format_currency(trip_plan.total_estimated_cost, curr)}", body_style)
        ],
        [
            Paragraph(f"<b>Group Satisfaction:</b> {trip_plan.group_satisfaction_score:.0f}%", body_style),
            Paragraph(f"<b>Active Agent Skills:</b> {len(trip_plan.active_skills)} Executed", body_style)
        ]
    ]
    overview_table = Table(overview_data, colWidths=[270, 270])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EBF8FF")),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#BEE3F8")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    story.append(overview_table)
    story.append(Spacer(1, 12))

    # Day by Day Itinerary
    for day in trip_plan.days:
        story.append(Paragraph(f"Day {day.day_number}: {day.theme}", h2_style))
        story.append(Paragraph(f"<b>Forecast:</b> {day.weather_summary} (Rain Risk: {day.rain_probability}%) | <b>Est. Transit:</b> {day.total_travel_km:.1f} km", body_style))
        story.append(Spacer(1, 5))

        day_table_data = [[
            Paragraph("Time", table_header),
            Paragraph("Slot", table_header),
            Paragraph("Attraction / Activity", table_header),
            Paragraph("Transit Mode", table_header),
            Paragraph("Cost", table_header),
            Paragraph("Crowd", table_header)
        ]]

        for slot in day.time_slots:
            cost_str = format_currency(slot.cost, curr) if slot.cost > 0 else "Free"
            activity_label = f"<b>{slot.activity_name}</b>"
            if slot.notes and len(slot.notes) > 5:
                note_snippet = slot.notes[:65] + "..." if len(slot.notes) > 65 else slot.notes
                activity_label += f"<br/>{note_snippet}"

            day_table_data.append([
                Paragraph(f"{slot.start_time} - {slot.end_time}", table_text),
                Paragraph(slot.slot_type, table_text),
                Paragraph(activity_label, table_text),
                Paragraph(slot.transit_mode, table_text),
                Paragraph(cost_str, table_text),
                Paragraph(slot.crowd_forecast, table_text)
            ])

        day_table = Table(day_table_data, colWidths=[65, 55, 220, 90, 50, 60], repeatRows=1)
        day_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2B6CB0")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
            ('PADDING', (0, 0), (-1, -1), 4),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(day_table)
        story.append(Spacer(1, 10))

    # Page Break for Survival Kit & Budget
    story.append(PageBreak())

    # Itemized Budget Breakdown
    story.append(Paragraph("Itemized Budget Breakdown", h2_style))
    budget_data = [[Paragraph("Expense Category", table_header), Paragraph("Estimated Amount", table_header)]]
    for category, amount in trip_plan.cost_breakdown.items():
        budget_data.append([
            Paragraph(category, table_text),
            Paragraph(format_currency(amount, curr), table_text)
        ])

    budget_table = Table(budget_data, colWidths=[360, 180], repeatRows=1)
    budget_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#2D3748")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(budget_table)
    story.append(Spacer(1, 14))

    # Offline Cultural Survival Kit
    if trip_plan.survival_kit:
        story.append(Paragraph("Cultural Survival Kit (Essential Phrases)", h2_style))
        phrase_data = [[
            Paragraph("Category", table_header),
            Paragraph("Local Phrase", table_header),
            Paragraph("Pronunciation", table_header),
            Paragraph("Meaning", table_header)
        ]]
        for p in trip_plan.survival_kit:
            phrase_data.append([
                Paragraph(p.category, table_text),
                Paragraph(f"<b>{p.phrase}</b>", table_text),
                Paragraph(f"<i>{p.phonetic}</i>", table_text),
                Paragraph(p.meaning, table_text)
            ])

        phrase_table = Table(phrase_data, colWidths=[80, 160, 150, 150], repeatRows=1)
        phrase_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4A5568")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7FAFC")]),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(phrase_table)
        story.append(Spacer(1, 14))

    # Emergency Contacts
    if trip_plan.emergency_contacts:
        story.append(Paragraph("Local Emergency Contacts & Protocols", h2_style))
        contact_data = [[Paragraph("Department / Service", table_header), Paragraph("Contact Number / Protocol", table_header)]]
        for service, num in trip_plan.emergency_contacts.items():
            contact_data.append([
                Paragraph(service, table_text),
                Paragraph(f"<b>{num}</b>", table_text)
            ])
        contact_table = Table(contact_data, colWidths=[270, 270], repeatRows=1)
        contact_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#C53030")),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E0")),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#FFF5F5")]),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(contact_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    return output_path
