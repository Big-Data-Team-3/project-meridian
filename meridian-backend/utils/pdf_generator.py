"""
PDF generation utility for Meridian Agents analysis reports.
Generates PDF from existing analysis results displayed on screen.
"""
from io import BytesIO
from typing import Dict, Any
from datetime import datetime
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


def generate_analysis_pdf(company: str, date: str, decision: str, state: Dict[str, Any]) -> BytesIO:
    """
    Generate a PDF report from analysis results.
    
    Args:
        company: Company name or ticker
        date: Trade date
        decision: Trading decision (BUY, SELL, HOLD)
        state: Complete graph state with all agent outputs
        
    Returns:
        BytesIO object containing the PDF
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError(
            "reportlab is required for PDF generation. "
            "Install it with: pip install reportlab"
        )
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Container for the 'Flowable' objects
    story = []
    
    # Define styles with improved formatting
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#1a365d'),
        spaceAfter=10,
        spaceBefore=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#4a5568'),
        spaceAfter=25,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    section_heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=15,
        spaceBefore=25,
        fontName='Helvetica-Bold',
        borderPadding=(0, 0, 5, 0),
        borderColor=colors.HexColor('#3182ce'),
        borderWidth=2,
        leftIndent=0,
        rightIndent=0
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#2d3748'),
        spaceAfter=10,
        spaceBefore=15,
        fontName='Helvetica-Bold',
        leftIndent=10
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#2d3748'),
        leading=16,
        alignment=TA_JUSTIFY,
        spaceBefore=5,
        spaceAfter=10,
        leftIndent=10,
        rightIndent=10
    )
    
    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#2d3748'),
        leading=14,
        leftIndent=25,
        spaceBefore=3,
        spaceAfter=3
    )
    
    # Decision color mapping
    decision_colors = {
        'BUY': colors.HexColor('#27ae60'),
        'SELL': colors.HexColor('#e74c3c'),
        'HOLD': colors.HexColor('#f39c12')
    }
    decision_color = decision_colors.get(decision.upper(), colors.HexColor('#7f8c8d'))
    
    # Header with decorative border
    story.append(Paragraph("MERIDIAN", title_style))
    story.append(Paragraph("Investment Analysis Report", subtitle_style))
    
    # Company Info Box with better styling
    info_data = [
        ['Company:', f'<b>{company.upper()}</b>'],
        ['Date:', date],
        ['Recommendation:', f'<b>{decision.upper()}</b>']
    ]
    
    info_table = Table(info_data, colWidths=[1.5*inch, 5*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#edf2f7')),
        ('BACKGROUND', (1, 0), (1, -1), colors.white),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2d3748')),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, 1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 15),
        ('RIGHTPADDING', (0, 0), (-1, -1), 15),
        ('BOX', (0, 0), (-1, -1), 1.5, colors.HexColor('#cbd5e0')),
        ('LINEBELOW', (0, 0), (-1, 1), 0.5, colors.HexColor('#e2e8f0')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    # Highlight decision row with color
    decision_bg_colors = {
        'BUY': colors.HexColor('#c6f6d5'),
        'SELL': colors.HexColor('#fed7d7'),
        'HOLD': colors.HexColor('#fef5e7')
    }
    decision_bg = decision_bg_colors.get(decision.upper(), colors.white)
    
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (1, 2), (1, 2), decision_bg),
        ('TEXTCOLOR', (1, 2), (1, 2), decision_color),
        ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 2), (1, 2), 13),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.4*inch))
    
    # Executive Summary with icon
    story.append(Paragraph("📋 EXECUTIVE SUMMARY", section_heading_style))
    decision_para = Paragraph(
        f"<b>Final Recommendation: <font color='{decision_color.hexval()}'>{decision.upper()}</font></b>",
        body_style
    )
    story.append(decision_para)
    story.append(Spacer(1, 0.15*inch))
    
    # Section 1: Market Analysis
    if state.get('market_report'):
        story.append(Paragraph("📊 MARKET ANALYSIS", section_heading_style))
        market_text = _sanitize_text(state['market_report'])
        story.append(Paragraph(market_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Section 2: Fundamentals Analysis
    if state.get('fundamentals_report'):
        story.append(Paragraph("💼 FUNDAMENTALS ANALYSIS", section_heading_style))
        fundamentals_text = _sanitize_text(state['fundamentals_report'])
        story.append(Paragraph(fundamentals_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Section 3: Information & Sentiment Analysis
    if state.get('information_report'):
        story.append(Paragraph("💬 SENTIMENT & INFORMATION ANALYSIS", section_heading_style))
        info_text = _sanitize_text(state['information_report'])
        story.append(Paragraph(info_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    elif state.get('sentiment_report'):
        story.append(Paragraph("💬 SENTIMENT ANALYSIS", section_heading_style))
        sentiment_text = _sanitize_text(state['sentiment_report'])
        story.append(Paragraph(sentiment_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    if state.get('news_report') and not state.get('information_report'):
        story.append(Paragraph("📰 NEWS ANALYSIS", section_heading_style))
        news_text = _sanitize_text(state['news_report'])
        story.append(Paragraph(news_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Section 4: Investment Debate
    if state.get('investment_debate_state'):
        debate_state = state['investment_debate_state']
        story.append(Paragraph("⚖️ INVESTMENT STRATEGY DEBATE", section_heading_style))
        
        if debate_state.get('bull_history'):
            story.append(Paragraph("🐂 Bull Case", subheading_style))
            bull_text = _sanitize_text(debate_state['bull_history'])
            story.append(Paragraph(bull_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        
        if debate_state.get('bear_history'):
            story.append(Paragraph("🐻 Bear Case", subheading_style))
            bear_text = _sanitize_text(debate_state['bear_history'])
            story.append(Paragraph(bear_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        
        if debate_state.get('judge_decision'):
            story.append(Paragraph("👨‍⚖️ Research Manager Decision", subheading_style))
            judge_text = _sanitize_text(debate_state['judge_decision'])
            story.append(Paragraph(judge_text, body_style))
            story.append(Spacer(1, 0.2*inch))
    
    # Section 5: Risk Analysis
    if state.get('risk_debate_state'):
        risk_state = state['risk_debate_state']
        story.append(Paragraph("⚠️ RISK ANALYSIS", section_heading_style))
        
        if risk_state.get('risky_history'):
            story.append(Paragraph("🔥 Aggressive Risk Perspective", subheading_style))
            risky_text = _sanitize_text(risk_state['risky_history'])
            story.append(Paragraph(risky_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        
        if risk_state.get('safe_history'):
            story.append(Paragraph("🛡️ Conservative Risk Perspective", subheading_style))
            safe_text = _sanitize_text(risk_state['safe_history'])
            story.append(Paragraph(safe_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        
        if risk_state.get('neutral_history'):
            story.append(Paragraph("⚖️ Balanced Risk Perspective", subheading_style))
            neutral_text = _sanitize_text(risk_state['neutral_history'])
            story.append(Paragraph(neutral_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        
        if risk_state.get('judge_decision'):
            story.append(Paragraph("👔 Risk Manager Decision", subheading_style))
            risk_judge_text = _sanitize_text(risk_state['judge_decision'])
            story.append(Paragraph(risk_judge_text, body_style))
            story.append(Spacer(1, 0.2*inch))
    
    # Section 6: Trading Strategy
    if state.get('trader_investment_plan'):
        story.append(Paragraph("📈 TRADING STRATEGY", section_heading_style))
        trader_plan_text = _sanitize_text(state['trader_investment_plan'])
        story.append(Paragraph(trader_plan_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    elif state.get('investment_plan'):
        story.append(Paragraph("📈 INVESTMENT PLAN", section_heading_style))
        plan_text = _sanitize_text(state['investment_plan'])
        story.append(Paragraph(plan_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Section 7: Final Recommendation
    if state.get('final_trade_decision'):
        story.append(Paragraph("🎯 FINAL RECOMMENDATION", section_heading_style))
        final_decision_text = _sanitize_text(state['final_trade_decision'])
        story.append(Paragraph(final_decision_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Footer with separator line
    story.append(Spacer(1, 0.4*inch))
    
    # Add horizontal line
    from reportlab.platypus import HRFlowable
    story.append(HRFlowable(
        width="100%",
        thickness=1,
        color=colors.HexColor('#cbd5e0'),
        spaceAfter=10,
        spaceBefore=10
    ))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#718096'),
        alignment=TA_CENTER,
        spaceAfter=5
    )
    
    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#a0aec0'),
        alignment=TA_CENTER,
        leading=11
    )
    
    footer_text = f"<b>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</b>"
    story.append(Paragraph(footer_text, footer_style))
    story.append(Paragraph("Meridian AI Trading Agents • Autonomous Financial Intelligence", footer_style))
    story.append(Spacer(1, 0.1*inch))
    story.append(Paragraph(
        "This report is for informational purposes only and does not constitute financial advice. "
        "Please consult with a qualified financial advisor before making investment decisions.",
        disclaimer_style
    ))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def _sanitize_text(text: str) -> str:
    """
    Sanitize and format text for PDF generation.
    Handles markdown-like formatting and converts to ReportLab HTML.
    """
    if not text:
        return ""
    
    text = str(text)
    import re
    
    # First, convert markdown bold (do this before italic to avoid conflicts)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__', r'<b>\1</b>', text)
    
    # Convert markdown italic (simpler pattern without lookbehind)
    # This will catch single * or _ that aren't part of bold
    text = re.sub(r'(?<!\*)\*(?!\*)([^\*]+?)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_(?!_)([^_]+?)_(?!_)', r'<i>\1</i>', text)
    
    # Remove markdown headers but keep the text (headers are handled by section titles)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    # Handle bullet points
    text = re.sub(r'^\s*[\-\*•]\s+', '  • ', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*\d+\.\s+', '  • ', text, flags=re.MULTILINE)
    
    # Handle tables - convert markdown tables to simple text
    lines = text.split('\n')
    cleaned_lines = []
    in_table = False
    for line in lines:
        if '|' in line and ('---' in line or line.count('|') >= 2):
            # Skip table separator lines
            if '---' in line:
                continue
            # Convert table rows to bullet points
            cells = [cell.strip() for cell in line.split('|') if cell.strip()]
            if cells:
                cleaned_lines.append('  • ' + ' | '.join(cells))
            in_table = True
        else:
            if in_table and line.strip() == '':
                in_table = False
            cleaned_lines.append(line)
    
    text = '\n'.join(cleaned_lines)
    
    # Convert newlines to line breaks
    text = text.replace('\n\n\n', '<br/><br/>')
    text = text.replace('\n\n', '<br/><br/>')
    text = text.replace('\n', '<br/>')
    
    # Clean up multiple line breaks
    text = re.sub(r'(<br/>){4,}', '<br/><br/>', text)
    
    # Remove any stray HTML tags that might cause issues (except b, i, br)
    text = re.sub(r'<(?!/?[bi]|br/?)([^>]+)>', '', text)
    
    return text
