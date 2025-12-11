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
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=12
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubHeading',
        parent=styles['Heading3'],
        fontSize=14,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=8,
        spaceBefore=8
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#2c3e50'),
        leading=14,
        alignment=TA_JUSTIFY
    )
    
    # Decision color mapping
    decision_colors = {
        'BUY': colors.HexColor('#27ae60'),
        'SELL': colors.HexColor('#e74c3c'),
        'HOLD': colors.HexColor('#f39c12')
    }
    decision_color = decision_colors.get(decision.upper(), colors.HexColor('#7f8c8d'))
    
    # Title
    story.append(Paragraph("Meridian Trading Analysis Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Company and Date Info
    info_data = [
        ['Company:', company.upper()],
        ['Analysis Date:', date],
        ['Trading Decision:', decision.upper()]
    ]
    
    info_table = Table(info_data, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#2c3e50')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#bdc3c7')),
    ]))
    
    # Highlight decision row
    info_table.setStyle(TableStyle([
        ('TEXTCOLOR', (1, 2), (1, 2), decision_color),
        ('FONTNAME', (1, 2), (1, 2), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 2), (1, 2), 14),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    decision_para = Paragraph(
        f"<b>Trading Decision: <font color='{decision_color.hexval()}'>{decision.upper()}</font></b>",
        body_style
    )
    story.append(decision_para)
    story.append(Spacer(1, 0.1*inch))
    
    # Market Analysis
    if state.get('market_report'):
        story.append(Paragraph("Market Analysis", heading_style))
        market_text = _sanitize_text(state['market_report'])
        story.append(Paragraph(market_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Fundamentals Analysis
    if state.get('fundamentals_report'):
        story.append(Paragraph("Fundamentals Analysis", heading_style))
        fundamentals_text = _sanitize_text(state['fundamentals_report'])
        story.append(Paragraph(fundamentals_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Information/Sentiment Analysis
    if state.get('sentiment_report'):
        story.append(Paragraph("Sentiment Analysis", heading_style))
        sentiment_text = _sanitize_text(state['sentiment_report'])
        story.append(Paragraph(sentiment_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    if state.get('news_report'):
        story.append(Paragraph("News Analysis", heading_style))
        news_text = _sanitize_text(state['news_report'])
        story.append(Paragraph(news_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Investment Debate
    if state.get('investment_debate_state'):
        debate_state = state['investment_debate_state']
        story.append(Paragraph("Investment Debate", heading_style))
        
        if debate_state.get('bull_history'):
            story.append(Paragraph("Bull Case", subheading_style))
            bull_text = _sanitize_text(debate_state['bull_history'])
            story.append(Paragraph(bull_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        
        if debate_state.get('bear_history'):
            story.append(Paragraph("Bear Case", subheading_style))
            bear_text = _sanitize_text(debate_state['bear_history'])
            story.append(Paragraph(bear_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        
        if debate_state.get('judge_decision'):
            story.append(Paragraph("Judge Decision", subheading_style))
            judge_text = _sanitize_text(debate_state['judge_decision'])
            story.append(Paragraph(judge_text, body_style))
            story.append(Spacer(1, 0.2*inch))
    
    # Risk Analysis
    if state.get('risk_debate_state'):
        risk_state = state['risk_debate_state']
        story.append(Paragraph("Risk Analysis", heading_style))
        
        if risk_state.get('risky_history'):
            story.append(Paragraph("Risky Perspective", subheading_style))
            risky_text = _sanitize_text(risk_state['risky_history'])
            story.append(Paragraph(risky_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        
        if risk_state.get('safe_history'):
            story.append(Paragraph("Safe Perspective", subheading_style))
            safe_text = _sanitize_text(risk_state['safe_history'])
            story.append(Paragraph(safe_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        
        if risk_state.get('judge_decision'):
            story.append(Paragraph("Risk Manager Decision", subheading_style))
            risk_judge_text = _sanitize_text(risk_state['judge_decision'])
            story.append(Paragraph(risk_judge_text, body_style))
            story.append(Spacer(1, 0.2*inch))
    
    # Final Investment Plan
    if state.get('investment_plan'):
        story.append(Paragraph("Final Investment Plan", heading_style))
        plan_text = _sanitize_text(state['investment_plan'])
        story.append(Paragraph(plan_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Final Trade Decision
    if state.get('final_trade_decision'):
        story.append(Paragraph("Final Trade Decision", heading_style))
        final_decision_text = _sanitize_text(state['final_trade_decision'])
        story.append(Paragraph(final_decision_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    
    # Footer
    story.append(Spacer(1, 0.3*inch))
    footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} by Meridian Trading Agents"
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#7f8c8d'),
        alignment=TA_CENTER
    )))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer


def _sanitize_text(text: str) -> str:
    """Sanitize text for PDF generation - escape HTML and handle newlines."""
    if not text:
        return ""
    # Replace newlines with <br/>
    text = str(text).replace('\n', '<br/>')
    # Escape HTML special characters
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    # But restore <br/> tags
    text = text.replace('&lt;br/&gt;', '<br/>')
    return text
