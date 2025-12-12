"""
PDF generation utility for Meridian Agents analysis reports.
Generates PDF from existing analysis results displayed on screen.
"""
import logging
from io import BytesIO
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)
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


def generate_analysis_pdf(company: str, date: str, decision: str, state: Dict[str, Any], agent_trace: Optional[Dict[str, Any]] = None) -> BytesIO:
    """
    Generate a PDF report from analysis results.
    
    Args:
        company: Company name or ticker
        date: Trade date
        decision: Trading decision (BUY, SELL, HOLD)
        state: Complete graph state with all agent outputs
        agent_trace: Optional agent trace with events and agent states
        
    Returns:
        BytesIO object containing the PDF
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError(
            "reportlab is required for PDF generation. "
            "Install it with: pip install reportlab"
        )
    
    # Log input parameters for debugging
    logger.info(f"PDF Generation Started - Company: {company}, Date: {date}, Decision: {decision}")
    logger.info(f"State type: {type(state)}, State keys: {list(state.keys()) if isinstance(state, dict) else 'N/A'}")
    logger.info(f"Agent trace provided: {agent_trace is not None}")
    if agent_trace:
        logger.info(f"Agent trace keys: {list(agent_trace.keys()) if isinstance(agent_trace, dict) else 'N/A'}")
        logger.info(f"Agents called: {agent_trace.get('agents_called', [])}")
        logger.info(f"Trace events count: {len(agent_trace.get('events', []))}")
    
    # Normalize state structure - handle cases where reports are nested in a 'reports' key
    if isinstance(state, dict) and 'reports' in state and isinstance(state.get('reports'), dict):
        logger.info("Found 'reports' key in state, extracting nested reports...")
        reports = state['reports']
        logger.info(f"Reports keys: {list(reports.keys())}")
        # Map nested reports to expected flat structure
        # Handle various possible key names
        if 'market' in reports:
            state['market_report'] = reports['market']
        elif 'market_report' in reports:
            state['market_report'] = reports['market_report']
            
        if 'fundamentals' in reports:
            state['fundamentals_report'] = reports['fundamentals']
        elif 'fundamentals_report' in reports:
            state['fundamentals_report'] = reports['fundamentals_report']
            
        if 'news' in reports:
            state['news_report'] = reports['news']
        elif 'news_report' in reports:
            state['news_report'] = reports['news_report']
            
        if 'sentiment' in reports:
            state['sentiment_report'] = reports['sentiment']
        elif 'sentiment_report' in reports:
            state['sentiment_report'] = reports['sentiment_report']
            
        if 'information' in reports:
            state['information_report'] = reports['information']
        elif 'information_report' in reports:
            state['information_report'] = reports['information_report']
            
        logger.info(f"Extracted reports from nested structure. New state keys: {list(state.keys())}")
    
    # Also check if state itself is nested (state.state pattern)
    if isinstance(state, dict) and 'state' in state and isinstance(state.get('state'), dict):
        logger.info("Found nested 'state' key, using inner state...")
        inner_state = state['state']
        # Merge inner state into outer state (inner state takes precedence)
        for key, value in inner_state.items():
            if key not in ['date', 'company', 'decision', 'response']:  # Don't overwrite top-level metadata
                state[key] = value
        logger.info(f"Merged nested state. Final state keys: {list(state.keys())}")
    
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
    market_report = state.get('market_report')
    if market_report:
        logger.info(f"✓ Including market_report (length: {len(str(market_report))} chars)")
        story.append(Paragraph("📊 MARKET ANALYSIS", section_heading_style))
        market_text = _sanitize_text(market_report)
        story.append(Paragraph(market_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    else:
        logger.warning("✗ market_report not found in state")
    
    # Section 2: Fundamentals Analysis
    fundamentals_report = state.get('fundamentals_report')
    if fundamentals_report:
        logger.info(f"✓ Including fundamentals_report (length: {len(str(fundamentals_report))} chars)")
        story.append(Paragraph("💼 FUNDAMENTALS ANALYSIS", section_heading_style))
        fundamentals_text = _sanitize_text(fundamentals_report)
        story.append(Paragraph(fundamentals_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    else:
        logger.warning("✗ fundamentals_report not found in state")
    
    # Section 3: Information & Sentiment Analysis
    information_report = state.get('information_report')
    sentiment_report = state.get('sentiment_report')
    news_report = state.get('news_report')
    
    if information_report:
        logger.info(f"✓ Including information_report (length: {len(str(information_report))} chars)")
        story.append(Paragraph("💬 SENTIMENT & INFORMATION ANALYSIS", section_heading_style))
        info_text = _sanitize_text(information_report)
        story.append(Paragraph(info_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    elif sentiment_report:
        logger.info(f"✓ Including sentiment_report (length: {len(str(sentiment_report))} chars)")
        story.append(Paragraph("💬 SENTIMENT ANALYSIS", section_heading_style))
        sentiment_text = _sanitize_text(sentiment_report)
        story.append(Paragraph(sentiment_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    else:
        logger.warning("✗ Neither information_report nor sentiment_report found in state")
    
    if news_report and not information_report:
        logger.info(f"✓ Including news_report (length: {len(str(news_report))} chars)")
        story.append(Paragraph("📰 NEWS ANALYSIS", section_heading_style))
        news_text = _sanitize_text(news_report)
        story.append(Paragraph(news_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    elif news_report:
        logger.info(f"ℹ news_report found but skipped (information_report already included)")
    else:
        logger.warning("✗ news_report not found in state")
    
    # Section 4: Investment Debate
    investment_debate_state = state.get('investment_debate_state')
    if investment_debate_state:
        logger.info(f"✓ Including investment_debate_state (type: {type(investment_debate_state)})")
        if isinstance(investment_debate_state, dict):
            logger.info(f"  - investment_debate_state keys: {list(investment_debate_state.keys())}")
        debate_state = investment_debate_state
        story.append(Paragraph("⚖️ INVESTMENT STRATEGY DEBATE", section_heading_style))
        
        bull_history = debate_state.get('bull_history') if isinstance(debate_state, dict) else None
        if bull_history:
            logger.info(f"  ✓ Including bull_history (length: {len(str(bull_history))} chars)")
            story.append(Paragraph("🐂 Bull Case", subheading_style))
            bull_text = _sanitize_text(bull_history)
            story.append(Paragraph(bull_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        else:
            logger.warning("  ✗ bull_history not found in investment_debate_state")
        
        bear_history = debate_state.get('bear_history') if isinstance(debate_state, dict) else None
        if bear_history:
            logger.info(f"  ✓ Including bear_history (length: {len(str(bear_history))} chars)")
            story.append(Paragraph("🐻 Bear Case", subheading_style))
            bear_text = _sanitize_text(bear_history)
            story.append(Paragraph(bear_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        else:
            logger.warning("  ✗ bear_history not found in investment_debate_state")
        
        judge_decision = debate_state.get('judge_decision') if isinstance(debate_state, dict) else None
        if judge_decision:
            logger.info(f"  ✓ Including judge_decision (length: {len(str(judge_decision))} chars)")
            story.append(Paragraph("👨‍⚖️ Research Manager Decision", subheading_style))
            judge_text = _sanitize_text(judge_decision)
            story.append(Paragraph(judge_text, body_style))
            story.append(Spacer(1, 0.2*inch))
        else:
            logger.warning("  ✗ judge_decision not found in investment_debate_state")
    else:
        logger.warning("✗ investment_debate_state not found in state")
    
    # Section 5: Risk Analysis
    risk_debate_state = state.get('risk_debate_state')
    if risk_debate_state:
        logger.info(f"✓ Including risk_debate_state (type: {type(risk_debate_state)})")
        if isinstance(risk_debate_state, dict):
            logger.info(f"  - risk_debate_state keys: {list(risk_debate_state.keys())}")
        risk_state = risk_debate_state
        story.append(Paragraph("⚠️ RISK ANALYSIS", section_heading_style))
        
        risky_history = risk_state.get('risky_history') if isinstance(risk_state, dict) else None
        if risky_history:
            logger.info(f"  ✓ Including risky_history (length: {len(str(risky_history))} chars)")
            story.append(Paragraph("🔥 Aggressive Risk Perspective", subheading_style))
            risky_text = _sanitize_text(risky_history)
            story.append(Paragraph(risky_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        else:
            logger.warning("  ✗ risky_history not found in risk_debate_state")
        
        safe_history = risk_state.get('safe_history') if isinstance(risk_state, dict) else None
        if safe_history:
            logger.info(f"  ✓ Including safe_history (length: {len(str(safe_history))} chars)")
            story.append(Paragraph("🛡️ Conservative Risk Perspective", subheading_style))
            safe_text = _sanitize_text(safe_history)
            story.append(Paragraph(safe_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        else:
            logger.warning("  ✗ safe_history not found in risk_debate_state")
        
        neutral_history = risk_state.get('neutral_history') if isinstance(risk_state, dict) else None
        if neutral_history:
            logger.info(f"  ✓ Including neutral_history (length: {len(str(neutral_history))} chars)")
            story.append(Paragraph("⚖️ Balanced Risk Perspective", subheading_style))
            neutral_text = _sanitize_text(neutral_history)
            story.append(Paragraph(neutral_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        else:
            logger.warning("  ✗ neutral_history not found in risk_debate_state")
        
        risk_judge_decision = risk_state.get('judge_decision') if isinstance(risk_state, dict) else None
        if risk_judge_decision:
            logger.info(f"  ✓ Including judge_decision (length: {len(str(risk_judge_decision))} chars)")
            story.append(Paragraph("👔 Risk Manager Decision", subheading_style))
            risk_judge_text = _sanitize_text(risk_judge_decision)
            story.append(Paragraph(risk_judge_text, body_style))
            story.append(Spacer(1, 0.2*inch))
        else:
            logger.warning("  ✗ judge_decision not found in risk_debate_state")
    else:
        logger.warning("✗ risk_debate_state not found in state")
    
    # Section 6: Trading Strategy
    trader_investment_plan = state.get('trader_investment_plan')
    investment_plan = state.get('investment_plan')
    
    if trader_investment_plan:
        logger.info(f"✓ Including trader_investment_plan (length: {len(str(trader_investment_plan))} chars)")
        story.append(Paragraph("📈 TRADING STRATEGY", section_heading_style))
        trader_plan_text = _sanitize_text(trader_investment_plan)
        story.append(Paragraph(trader_plan_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    elif investment_plan:
        logger.info(f"✓ Including investment_plan (length: {len(str(investment_plan))} chars)")
        story.append(Paragraph("📈 INVESTMENT PLAN", section_heading_style))
        plan_text = _sanitize_text(investment_plan)
        story.append(Paragraph(plan_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    else:
        logger.warning("✗ Neither trader_investment_plan nor investment_plan found in state")
    
    # Section 7: Final Recommendation
    final_trade_decision = state.get('final_trade_decision')
    if final_trade_decision:
        logger.info(f"✓ Including final_trade_decision (length: {len(str(final_trade_decision))} chars)")
        story.append(Paragraph("🎯 FINAL RECOMMENDATION", section_heading_style))
        final_decision_text = _sanitize_text(final_trade_decision)
        story.append(Paragraph(final_decision_text, body_style))
        story.append(Spacer(1, 0.2*inch))
    else:
        logger.warning("✗ final_trade_decision not found in state")
    
    # Section 8: Agent Trace with All States
    if agent_trace:
        story.append(Paragraph("🔍 AGENT EXECUTION TRACE", section_heading_style))
        
        # All 11 agents in the system
        all_agents = [
            "Market Analyst",
            "Fundamentals Analyst", 
            "Information Analyst",
            "Bull Researcher",
            "Bear Researcher",
            "Research Manager",
            "Risky Debator",
            "Safe Debator",
            "Neutral Debator",
            "Risk Manager",
            "Trader"
        ]
        
        # Display agents called
        agents_called = agent_trace.get('agents_called', [])
        if agents_called:
            story.append(Paragraph(f"<b>Agents Executed ({len(agents_called)}):</b>", subheading_style))
            agents_text = ", ".join(agents_called)
            story.append(Paragraph(agents_text, body_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Show which agents were NOT called
            agents_not_called = [a for a in all_agents if a not in agents_called]
            if agents_not_called:
                story.append(Paragraph(f"<b>Agents Not Executed ({len(agents_not_called)}):</b>", subheading_style))
                not_called_text = ", ".join(agents_not_called)
                story.append(Paragraph(f"<i>{not_called_text}</i>", body_style))
                story.append(Spacer(1, 0.15*inch))
        else:
            story.append(Paragraph(f"<b>All Available Agents ({len(all_agents)}):</b>", subheading_style))
            all_agents_text = ", ".join(all_agents)
            story.append(Paragraph(all_agents_text, body_style))
            story.append(Spacer(1, 0.15*inch))
        
        # Display workflow and intent
        workflow = agent_trace.get('workflow', 'N/A')
        intent = agent_trace.get('intent', 'N/A')
        story.append(Paragraph(f"<b>Workflow:</b> {workflow} | <b>Intent:</b> {intent}", body_style))
        story.append(Spacer(1, 0.15*inch))
        
        # Display all trace events
        events = agent_trace.get('events', [])
        if events:
            story.append(Paragraph(f"<b>Execution Events ({len(events)} total):</b>", subheading_style))
            
            # Group events by agent
            agent_events = {}
            for event in events:
                agent_name = event.get('agent_name', 'System')
                if agent_name not in agent_events:
                    agent_events[agent_name] = []
                agent_events[agent_name].append(event)
            
            # Display events grouped by agent
            for agent_name, agent_event_list in agent_events.items():
                story.append(Paragraph(f"<b>🤖 {agent_name}:</b>", subheading_style))
                
                for idx, event in enumerate(agent_event_list, 1):
                    event_type = event.get('event_type', 'unknown')
                    message = event.get('message', '')
                    timestamp = event.get('timestamp', '')
                    progress = event.get('progress')
                    event_data = event.get('data', {})
                    
                    # Format event details
                    event_details = []
                    if timestamp:
                        try:
                            # Parse and format timestamp
                            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                            event_details.append(f"Time: {dt.strftime('%H:%M:%S')}")
                        except:
                            event_details.append(f"Time: {timestamp[:19] if len(timestamp) > 19 else timestamp}")
                    
                    if progress is not None:
                        event_details.append(f"Progress: {progress}%")
                    
                    event_info = f"<b>[{event_type.upper()}]</b> {message}"
                    if event_details:
                        event_info += f" ({', '.join(event_details)})"
                    
                    story.append(Paragraph(f"  {idx}. {event_info}", bullet_style))
                    
                    # Include state data if available in event
                    if event_data and isinstance(event_data, dict):
                        state_keys = [k for k in event_data.keys() if 'state' in k.lower() or 'report' in k.lower() or 'decision' in k.lower()]
                        if state_keys:
                            state_info = ", ".join(state_keys[:5])  # Limit to first 5 keys
                            if len(state_keys) > 5:
                                state_info += f" ... (+{len(state_keys) - 5} more)"
                            story.append(Paragraph(f"     <i>State keys: {state_info}</i>", bullet_style))
                
                story.append(Spacer(1, 0.1*inch))
            
            # Display all state keys from the complete state
            story.append(Paragraph("<b>📊 Complete State Keys:</b>", subheading_style))
            all_state_keys = list(state.keys())
            if all_state_keys:
                # Group state keys by category
                report_keys = [k for k in all_state_keys if 'report' in k.lower()]
                debate_keys = [k for k in all_state_keys if 'debate' in k.lower() or 'history' in k.lower()]
                decision_keys = [k for k in all_state_keys if 'decision' in k.lower() or 'plan' in k.lower()]
                other_keys = [k for k in all_state_keys if k not in report_keys + debate_keys + decision_keys]
                
                if report_keys:
                    story.append(Paragraph(f"<b>Reports:</b> {', '.join(report_keys)}", bullet_style))
                if debate_keys:
                    story.append(Paragraph(f"<b>Debates:</b> {', '.join(debate_keys)}", bullet_style))
                if decision_keys:
                    story.append(Paragraph(f"<b>Decisions:</b> {', '.join(decision_keys)}", bullet_style))
                if other_keys:
                    story.append(Paragraph(f"<b>Other:</b> {', '.join(other_keys)}", bullet_style))
            else:
                story.append(Paragraph("No state keys available", bullet_style))
            
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
    
    # Log summary of what was included
    logger.info("=" * 80)
    logger.info("PDF Generation Summary:")
    logger.info("=" * 80)
    
    # Count sections by checking for section headings
    section_count = sum(1 for p in story if isinstance(p, Paragraph) and hasattr(p, 'style') and p.style.name == 'SectionHeading')
    logger.info(f"  - Total sections added: {section_count}")
    logger.info(f"  - Total story elements: {len(story)}")
    
    # Count content sections that were actually included
    content_sections = []
    if state.get('market_report'):
        content_sections.append('Market Analysis')
    if state.get('fundamentals_report'):
        content_sections.append('Fundamentals Analysis')
    if state.get('information_report') or state.get('sentiment_report') or state.get('news_report'):
        content_sections.append('Information/Sentiment Analysis')
    if state.get('investment_debate_state'):
        content_sections.append('Investment Debate')
    if state.get('risk_debate_state'):
        content_sections.append('Risk Analysis')
    if state.get('trader_investment_plan') or state.get('investment_plan'):
        content_sections.append('Trading Strategy')
    if state.get('final_trade_decision'):
        content_sections.append('Final Recommendation')
    if agent_trace:
        content_sections.append('Agent Trace')
    
    logger.info(f"  - Content sections included: {len(content_sections)}")
    logger.info(f"    Sections: {', '.join(content_sections)}")
    logger.info(f"  - State keys available: {list(state.keys()) if isinstance(state, dict) else 'N/A'}")
    logger.info(f"  - Agent trace included: {agent_trace is not None}")
    
    # Build PDF
    logger.info("Building PDF document...")
    try:
        doc.build(story)
        buffer.seek(0)
        pdf_size = len(buffer.getvalue())
        logger.info(f"✓ PDF generated successfully (size: {pdf_size:,} bytes)")
        logger.info("=" * 80)
        return buffer
    except Exception as e:
        logger.error(f"✗ PDF build failed: {e}", exc_info=True)
        raise


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
    
    # STEP 1: First, normalize ALL existing br tags (from incoming HTML) to newlines
    # This ensures we start with clean text
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<br\s+/>', '\n', text, flags=re.IGNORECASE)
    
    # STEP 2: Normalize newlines (collapse multiple newlines)
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
    
    # STEP 3: Convert newlines to <br/> tags (ReportLab accepts <br/>)
    # But we need to ensure they're properly formatted
    text = text.replace('\n\n', '<br/><br/>')  # Double newline = paragraph break
    text = text.replace('\n', '<br/>')  # Single newline = line break
    
    # STEP 4: Clean up excessive consecutive br tags
    text = re.sub(r'(<br/>){4,}', '<br/><br/>', text)
    
    # STEP 5: Remove any stray HTML tags (except b, i, br)
    text = re.sub(r'<(?!/?[bi]|br/?)([^>]+)>', '', text)
    
    # STEP 6: Final check - ensure br tags are properly formatted
    # ReportLab's parser is strict - ensure no spaces or issues around br tags
    # Remove any whitespace immediately after <br/> tags
    text = re.sub(r'<br/>\s+', '<br/>', text)
    
    return text
