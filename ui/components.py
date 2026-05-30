import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional
import io
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute total pages and draw footer with page numbers.
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
            self.draw_page_number(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_page_number(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#64748b"))
        
        # Header
        self.setStrokeColor(colors.HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(54, 738, 558, 738)
        self.drawString(54, 744, "AI FINANCIAL STATEMENT ANALYZER")
        
        # Footer
        self.line(54, 54, 558, 54)
        self.drawString(54, 40, "Confidential - Investment Research Report")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(558, 40, page_text)
        
        self.restoreState()


def render_recommendation_panel(rec_data: Dict[str, Any], strength_data: Dict[str, Any], company_name: str):
    """
    Renders the investment rating, reasoning, strengths, weaknesses,
    growth indicators, and detailed investment thesis.
    All HTML is emitted in a single st.markdown call per block to prevent
    Streamlit from auto-closing divs across separate calls.
    """
    rec = rec_data.get("recommendation", "Moderate Risk")
    reasoning = rec_data.get("reasoning", "") or "Analysis in progress..."
    strengths = rec_data.get("strengths", [])
    weaknesses = rec_data.get("weaknesses", [])
    growth_indicators = rec_data.get("growth_indicators", [])
    risk_analysis = rec_data.get("risk_analysis", [])
    thesis = rec_data.get("investment_thesis", "") or "Thesis generation in progress..."
    confidence = rec_data.get("confidence_score", 70)
    score = strength_data.get("score", 50)

    if rec == "Strong Buy":
        badge_color = "#22c55e"; badge_bg = "rgba(34,197,94,0.18)"; badge_border = "rgba(34,197,94,0.5)"
    elif rec == "Buy":
        badge_color = "#86efac"; badge_bg = "rgba(134,239,172,0.12)"; badge_border = "rgba(134,239,172,0.3)"
    elif rec == "Hold":
        badge_color = "#fbbf24"; badge_bg = "rgba(245,158,11,0.15)"; badge_border = "rgba(245,158,11,0.4)"
    elif rec == "Sell":
        badge_color = "#f97316"; badge_bg = "rgba(249,115,22,0.15)"; badge_border = "rgba(249,115,22,0.4)"
    else: # Avoid
        badge_color = "#ef4444"; badge_bg = "rgba(239,68,68,0.15)"; badge_border = "rgba(239,68,68,0.4)"

    # ── Header card ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="glass-card">
      <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:15px;margin-bottom:20px">
        <div>
          <span style="font-size:0.8rem;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8;display:block;margin-bottom:6px">INVESTMENT RATING</span>
          <span style="display:inline-flex;align-items:center;padding:8px 20px;border-radius:30px;font-weight:700;font-size:1.05rem;letter-spacing:.04em;
                       background:{badge_bg};color:{badge_color};border:1px solid {badge_border};box-shadow:0 0 14px {badge_bg}">
            {rec}
          </span>
        </div>
        <div style="text-align:right">
          <span style="font-size:0.8rem;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8;display:block;margin-bottom:6px">STOCK STRENGTH INDEX</span>
          <span style="font-size:2.4rem;font-weight:800;color:#60a5fa">{score}
            <span style="font-size:1rem;color:#64748b;font-weight:400"> / 100</span>
          </span>
        </div>
      </div>
      <hr style="border:0;border-top:1px solid rgba(255,255,255,0.1);margin-bottom:18px">
      <p style="font-size:0.8rem;text-transform:uppercase;letter-spacing:.06em;color:#94a3b8;margin-bottom:6px">EXECUTIVE SUMMARY</p>
      <p style="font-size:1rem;line-height:1.65;color:#e2e8f0;font-style:italic">&#8220;{reasoning}&#8221;</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Strengths & Weaknesses ─────────────────────────────────────────────
    col1, col2 = st.columns(2)
    with col1:
        s_items = "".join(f"<div style='margin-bottom:9px;font-size:0.91rem;line-height:1.5;color:#e2e8f0'>&#8226; {s}</div>" for s in strengths) or "<div style='color:#64748b;font-size:0.88rem'>No data available</div>"
        st.markdown(f"""
        <div class="glass-card" style="min-height:180px">
          <h4 style="color:#4ade80;margin-bottom:14px">&#10003; Key Strengths</h4>
          {s_items}
        </div>
        """, unsafe_allow_html=True)

    with col2:
        w_items = "".join(f"<div style='margin-bottom:9px;font-size:0.91rem;line-height:1.5;color:#e2e8f0'>&#8226; {w}</div>" for w in weaknesses) or "<div style='color:#64748b;font-size:0.88rem'>No data available</div>"
        st.markdown(f"""
        <div class="glass-card" style="min-height:180px">
          <h4 style="color:#f87171;margin-bottom:14px">&#9888; Key Weaknesses</h4>
          {w_items}
        </div>
        """, unsafe_allow_html=True)

    # ── Growth Indicators & Risk Factors ──────────────────────────────────
    col3, col4 = st.columns(2)
    with col3:
        g_items = "".join(f"<div style='margin-bottom:9px;font-size:0.91rem;line-height:1.5;color:#e2e8f0'>&#8226; {g}</div>" for g in growth_indicators) or "<div style='color:#64748b;font-size:0.88rem'>No data available</div>"
        st.markdown(f"""
        <div class="glass-card" style="min-height:180px">
          <h4 style="color:#60a5fa;margin-bottom:14px">&#128200; Growth Indicators</h4>
          {g_items}
        </div>
        """, unsafe_allow_html=True)

    with col4:
        r_items = "".join(f"<div style='margin-bottom:9px;font-size:0.91rem;line-height:1.5;color:#e2e8f0'>&#8226; {r}</div>" for r in risk_analysis) or "<div style='color:#64748b;font-size:0.88rem'>No data available</div>"
        st.markdown(f"""
        <div class="glass-card" style="min-height:180px">
          <h4 style="color:#fbbf24;margin-bottom:14px">&#128737; Risk Factors</h4>
          {r_items}
        </div>
        """, unsafe_allow_html=True)

    # ── Investment Thesis ─────────────────────────────────────────────────
    safe_thesis = thesis.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '<br>')
    st.markdown(f"""
    <div class="glass-card">
      <h4 style="color:#e2e8f0;margin-bottom:14px">&#128196; Investment Thesis Summary</h4>
      <div style="font-size:0.96rem;line-height:1.75;color:#cbd5e1">{safe_thesis}</div>
      <div style="margin-top:18px;font-size:0.8rem;color:#475569;text-align:right">LLM Analyst Confidence: {confidence}%</div>
    </div>
    """, unsafe_allow_html=True)


def render_kpi_cards(metrics_data: Dict[str, Any]):
    """
    Renders high-level financial KPI cards showing latest year's value
    and YoY percentage changes if available.
    """
    years = metrics_data.get("years", [])
    metrics = metrics_data.get("metrics", {})
    if not years:
        return
        
    latest_idx = -1
    prev_idx = -2 if len(years) > 1 else None
    
    kpis = [
        {"title": "Revenue", "key": "Revenue", "format": "₹{:,.0f} Cr"},
        {"title": "Net Profit", "key": "Net Profit", "format": "₹{:,.0f} Cr"},
        {"title": "EBITDA", "key": "EBITDA", "format": "₹{:,.0f} Cr"},
        {"title": "Total Debt", "key": "Total Debt", "format": "₹{:,.0f} Cr"},
        {"title": "Operating Cash Flow", "key": "Operating Cash Flow", "format": "₹{:,.0f} Cr"},
        {"title": "Free Cash Flow", "key": "Free Cash Flow", "format": "₹{:,.0f} Cr"}
    ]
    
    # 3x2 grid
    cols = st.columns(3)
    for i, kpi in enumerate(kpis):
        col = cols[i % 3]
        vals = metrics.get(kpi["key"], [])
        
        latest_val = vals[latest_idx] if len(vals) > 0 else None
        prev_val = vals[prev_idx] if prev_idx is not None and len(vals) > abs(prev_idx) else None
        
        if latest_val is None:
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-title">{kpi['title']}</div>
                    <div class="metric-value" style="color: rgba(255,255,255,0.25);">N/A</div>
                    <div class="metric-subtext">No historical records</div>
                </div>
                """, unsafe_allow_html=True)
            continue
            
        formatted_val = kpi["format"].format(latest_val) if latest_val >= 0 else "-" + kpi["format"].format(abs(latest_val))
        
        # Calculate YoY Change
        yoy_change = None
        yoy_text = "Latest Year"
        yoy_style = "color: rgba(255,255,255,0.4);"
        
        if prev_val and prev_val != 0:
            yoy_change = (latest_val - prev_val) / abs(prev_val)
            direction_symbol = "▲" if yoy_change > 0 else "▼"
            color = "#4ade80" if yoy_change > 0 else "#f87171"
            # Reverse for Debt
            if kpi["key"] == "Total Debt":
                color = "#f87171" if yoy_change > 0 else "#4ade80"
            yoy_text = f"{direction_symbol} {yoy_change:+.1%} YoY"
            yoy_style = f"color: {color}; font-weight: 600;"
            
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">{kpi['title']}</div>
                <div class="metric-value">{formatted_val}</div>
                <div class="metric-subtext" style="{yoy_style}">{yoy_text} ({years[latest_idx]})</div>
            </div>
            """, unsafe_allow_html=True)


def render_risk_flags(strength_data: Dict[str, Any]):
    """
    Renders risk warnings and diagnostics.
    """
    flags = strength_data.get("risk_flags", [])
    if not flags:
        st.success("No severe risk flags identified. Fundamental health is solid.")
        return
        
    for flag in flags:
        st.markdown(f"""
        <div class="risk-flag-container">
            <span style="font-size: 1.2rem;">🚨</span>
            <div class="risk-flag-text">{flag}</div>
        </div>
        """, unsafe_allow_html=True)


def render_stock_strength_index(strength_data: Dict[str, Any]):
    """
    Displays the Stock Strength Index breakdown score as a compact
    single-block HTML card to avoid Streamlit div auto-closing issues.
    """
    score = strength_data.get("score", 50)
    breakdown = strength_data.get("breakdown", {})
    
    category_max = {
        "Growth": 25,
        "Profitability": 20,
        "Cash Flow": 20,
        "Debt": 15,
        "Valuation": 10,
        "Capital Allocation": 10
    }

    # Build the breakdown bars purely in HTML
    bars_html = ""
    for cat, val in breakdown.items():
        max_val = category_max.get(cat, 20)
        pct = (val / max_val) * 100 if max_val > 0 else 0
        color = "#22c55e" if pct >= 75 else "#eab308" if pct >= 40 else "#ef4444"
        bars_html += f"""
<div style="margin-bottom:14px">
  <div style="display:flex;justify-content:space-between;margin-bottom:5px">
    <span style="font-size:0.87rem;font-weight:500;color:#cbd5e1">{cat}</span>
    <span style="font-size:0.82rem;font-weight:600;color:{color}">{val:.1f} / {max_val} pts</span>
  </div>
  <div style="background:rgba(255,255,255,0.07);border-radius:6px;height:8px;overflow:hidden">
    <div style="width:{pct:.0f}%;height:100%;background:{color};border-radius:6px;transition:width .4s ease"></div>
  </div>
</div>
"""

    st.markdown(f"""
<div class="glass-card">
  <h4 style="color:#e2e8f0;margin-bottom:6px">Stock Strength Index</h4>
  <p style="font-size:0.86rem;color:#94a3b8;margin-bottom:20px">
    Score of <strong style="color:#60a5fa">{score}/100</strong> — weighted aggregation of deterministic fundamental indicators.
  </p>
  {bars_html}
</div>
""", unsafe_allow_html=True)


def render_ratio_table(ratios_data: Dict[str, List[Any]], years: List[int]):
    """
    Renders ratio table.
    """
    # Keep only last 5 years data
    n_keep = 5
    years_plot = years[-n_keep:] if len(years) > n_keep else years
    
    # Build dataframe
    df_data = {}
    for ratio_name, vals in ratios_data.items():
        formatted_vals = []
        vals_plot = vals[-n_keep:] if len(vals) > n_keep else vals
        for val in vals_plot:
            if val is None:
                formatted_vals.append("-")
            elif ratio_name in ["Current Ratio", "Interest Coverage", "Debt-to-Equity"]:
                formatted_vals.append(f"{val:.2f}x")
            else:
                formatted_vals.append(f"{val:.2%}")
        df_data[ratio_name] = formatted_vals
        
    df = pd.DataFrame(df_data, index=years_plot)
    st.table(df.T)


def render_extracted_metrics(metrics_data: Dict[str, Any]):
    """
    Renders raw extracted metrics table.
    """
    years = metrics_data.get("years", [])
    metrics = metrics_data.get("metrics", {})
    
    n_keep = 5
    years_plot = years[-n_keep:] if len(years) > n_keep else years
    
    df_data = {}
    for m_name, vals in metrics.items():
        formatted_vals = []
        vals_plot = vals[-n_keep:] if len(vals) > n_keep else vals
        for v in vals_plot:
            if v is None:
                formatted_vals.append("-")
            else:
                formatted_vals.append(f"{v:,.2f}")
        df_data[m_name] = formatted_vals
        
    df = pd.DataFrame(df_data, index=years_plot)
    st.table(df.T)


def generate_pdf_report(
    company_name: str,
    rec_data: Dict[str, Any],
    strength_data: Dict[str, Any],
    ratios_data: Dict[str, List[Any]],
    metrics_data: Dict[str, Any]
) -> bytes:
    """
    Generates a production-quality PDF report using ReportLab.
    Returns bytes of the generated PDF.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=15
    )
    
    section_title_style = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'DocBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=10
    )
    
    bold_body_style = ParagraphStyle(
        'DocBodyBold',
        parent=body_style,
        fontName='Helvetica-Bold'
    )
    
    bullet_style = ParagraphStyle(
        'DocBullet',
        parent=body_style,
        leftIndent=15,
        firstLineIndent=-10,
        spaceAfter=5
    )

    story = []
    
    # Title
    story.append(Paragraph(f"Financial Statement Analysis Report", title_style))
    story.append(Paragraph(f"<b>Target Entity:</b> {company_name}", body_style))
    story.append(Paragraph(f"<b>Report Generated:</b> 2026-05-29", body_style))
    story.append(Spacer(1, 15))
    
    # Recommendation Box
    rec = rec_data.get("recommendation", "Moderate Risk")
    reasoning = rec_data.get("reasoning", "")
    score = strength_data.get("score", 50)
    
    if rec == "Strong Buy":
        rec_color = "#22c55e"
    elif rec == "Buy":
        rec_color = "#86efac"
    elif rec == "Hold":
        rec_color = "#fbbf24"
    elif rec == "Sell":
        rec_color = "#f97316"
    else:
        rec_color = "#ef4444"
    
    box_data = [
        [
            Paragraph(f"<b>Investment Rating:</b> <font color='{rec_color}'><b>{rec}</b></font>", bold_body_style),
            Paragraph(f"<b>Stock Strength Score:</b> <b>{score}/100</b>", bold_body_style)
        ]
    ]
    box_table = Table(box_data, colWidths=[252, 252])
    box_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('PADDING', (0,0), (-1,-1), 12),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#e2e8f0")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0"))
    ]))
    
    story.append(box_table)
    story.append(Spacer(1, 10))
    story.append(Paragraph(f"<b>Executive Summary:</b> <i>\"{reasoning}\"</i>", body_style))
    story.append(Spacer(1, 15))
    
    # Key Factors
    story.append(Paragraph("Rating Breakdown Details", section_title_style))
    
    story.append(Paragraph("<b>Core Strengths:</b>", bold_body_style))
    for s in rec_data.get("strengths", []):
        story.append(Paragraph(f"• {s}", bullet_style))
    story.append(Spacer(1, 5))
        
    story.append(Paragraph("<b>Primary Weaknesses & Risks:</b>", bold_body_style))
    for w in rec_data.get("weaknesses", []):
        story.append(Paragraph(f"• {w}", bullet_style))
    story.append(Spacer(1, 15))
    
    # Financial Ratios Table
    story.append(Paragraph("Key Financial Ratios", section_title_style))
    years = metrics_data.get("years", [])
    
    # Keep only last 5 years data
    n_keep = 5
    years_plot = years[-n_keep:] if len(years) > n_keep else years
    
    # Table headers
    headers = ["Ratio"] + [str(y) for y in years_plot]
    ratio_rows = []
    
    for r_name, vals in ratios_data.items():
        formatted_vals = []
        vals_plot = vals[-n_keep:] if len(vals) > n_keep else vals
        for val in vals_plot:
            if val is None:
                formatted_vals.append("-")
            elif r_name in ["Current Ratio", "Interest Coverage", "Debt-to-Equity"]:
                formatted_vals.append(f"{val:.2f}x")
            else:
                formatted_vals.append(f"{val:.1%}")
        ratio_rows.append([r_name] + formatted_vals)
        
    table_data = [headers] + ratio_rows
    col_w = [184] + [320 / len(years_plot)] * len(years_plot)
    
    ratio_table = Table(table_data, colWidths=col_w)
    ratio_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8fafc")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 9),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('PADDING', (0,0), (-1,-1), 6)
    ]))
    
    story.append(ratio_table)
    story.append(PageBreak())
    
    # Investment Thesis
    story.append(Paragraph("Investment Thesis & Qualitative Findings", section_title_style))
    thesis = rec_data.get("investment_thesis", "")
    story.append(Paragraph(thesis.replace('\n', '<br/>'), body_style))
    story.append(Spacer(1, 15))
    
    # Diagnostic / Risk Warnings
    flags = strength_data.get("risk_flags", [])
    if flags:
        story.append(Paragraph("Key Warnings & Risk Alerts", section_title_style))
        for flag in flags:
            story.append(Paragraph(f"<font color='red'><b>🚨</b></font> {flag}", bullet_style))
            
    # Build Document
    doc.build(story, canvasmaker=NumberedCanvas)
    
    buffer.seek(0)
    return buffer.getvalue()
