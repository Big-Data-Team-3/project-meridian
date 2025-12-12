'use client';

import { useState, type ReactElement } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';

interface AnalysisState {
  // Analyst Reports
  market_report?: string;
  fundamentals_report?: string;
  sentiment_report?: string;
  news_report?: string;
  information_report?: string;
  
  // Investment Debate
  investment_debate_state?: {
    bull_history?: string;
    bear_history?: string;
    judge_decision?: string;
  };
  
  // Trader Decision
  trader_investment_plan?: string;
  investment_plan?: string;
  
  // Risk Analysis
  risk_debate_state?: {
    risky_history?: string;
    safe_history?: string;
    neutral_history?: string;
    judge_decision?: string;
  };
  
  // Final Decision
  final_trade_decision?: string;
  
  // Any other fields
  [key: string]: any;
}

interface AnalysisBreakdownProps {
  state: AnalysisState;
  decision: string;
  company: string;
  date: string;
}

interface SectionProps {
  title: string;
  content: string | undefined;
  icon: string;
  defaultExpanded?: boolean;
}

function Section({ title, content, icon, defaultExpanded = false }: SectionProps): ReactElement | null {
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);
  
  if (!content || content.trim() === '') {
    return null;
  }
  
  return (
    <div className="border border-border rounded-lg overflow-hidden bg-surface">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-surface-hover transition-colors"
      >
        <div className="flex items-center gap-3">
          <span className="text-2xl">{icon}</span>
          <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        </div>
        <svg
          className={cn(
            'w-5 h-5 text-text-secondary transition-transform',
            isExpanded && 'transform rotate-180'
          )}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 9l-7 7-7-7"
          />
        </svg>
      </button>
      
      {isExpanded && (
        <div className="p-4 pt-0 border-t border-border">
          <div className="prose prose-sm max-w-none dark:prose-invert">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  );
}

export function AnalysisBreakdown({ state, decision, company, date }: AnalysisBreakdownProps): ReactElement {
  const [isDownloading, setIsDownloading] = useState(false);
  
  const decisionColors = {
    BUY: 'bg-green-500/20 text-green-600 border-green-500/30',
    SELL: 'bg-red-500/20 text-red-600 border-red-500/30',
    HOLD: 'bg-yellow-500/20 text-yellow-600 border-yellow-500/30',
  };
  
  const decisionColor = decisionColors[decision as keyof typeof decisionColors] || 'bg-surface text-text-primary border-border';
  
  const downloadPDF = async () => {
    setIsDownloading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/agents/pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          company,
          date,
          decision,
          state,
        }),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate PDF');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Meridian_${company}_Analysis_${date}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Error downloading PDF:', error);
      alert('Failed to download PDF. Please try again.');
    } finally {
      setIsDownloading(false);
    }
  };
  
  return (
    <div className="space-y-3 mt-4">
      {/* Decision Badge & Download Button */}
      <div className="flex items-center justify-between">
        <div className={cn('inline-flex items-center gap-2 px-4 py-2 rounded-lg border font-semibold', decisionColor)}>
          <span className="text-lg">
            {decision === 'BUY' && '📈'}
            {decision === 'SELL' && '📉'}
            {decision === 'HOLD' && '⏸️'}
          </span>
          <span>Decision: {decision}</span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={downloadPDF}
            disabled={isDownloading}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm bg-primary text-primary-foreground hover:bg-primary/90 rounded-lg border border-primary/20 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isDownloading ? (
              <>
                <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Generating...</span>
              </>
            ) : (
              <>
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span>Download PDF</span>
              </>
            )}
          </button>
          <div className="text-xs text-text-secondary">
            {company} • {date}
          </div>
        </div>
      </div>
      
      {/* Final Decision */}
      {state.final_trade_decision && (
        <Section
          title="Final Trading Decision"
          content={state.final_trade_decision}
          icon="🎯"
          defaultExpanded={true}
        />
      )}
      
      {/* Trader Investment Plan */}
      {state.trader_investment_plan && (
        <Section
          title="Trader Investment Plan"
          content={state.trader_investment_plan}
          icon="💼"
          defaultExpanded={!state.final_trade_decision} // Expand if no final decision
        />
      )}
      
      {/* Investment Plan from Research Manager */}
      {state.investment_plan && state.investment_plan !== state.trader_investment_plan && (
        <Section
          title="Investment Strategy"
          content={state.investment_plan}
          icon="📋"
        />
      )}
      
      {/* Risk Analysis */}
      {state.risk_debate_state && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Risk Analysis</h3>
          
          {state.risk_debate_state.judge_decision && (
            <Section
              title="Risk Manager Decision"
              content={state.risk_debate_state.judge_decision}
              icon="⚖️"
            />
          )}
          
          {state.risk_debate_state.risky_history && (
            <Section
              title="Aggressive Risk Perspective"
              content={state.risk_debate_state.risky_history}
              icon="🔥"
            />
          )}
          
          {state.risk_debate_state.safe_history && (
            <Section
              title="Conservative Risk Perspective"
              content={state.risk_debate_state.safe_history}
              icon="🛡️"
            />
          )}
          
          {state.risk_debate_state.neutral_history && (
            <Section
              title="Balanced Risk Perspective"
              content={state.risk_debate_state.neutral_history}
              icon="⚖️"
            />
          )}
        </div>
      )}
      
      {/* Investment Debate */}
      {state.investment_debate_state && (
        <div className="space-y-2">
          <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Investment Debate</h3>
          
          {state.investment_debate_state.judge_decision && (
            <Section
              title="Research Manager Decision"
              content={state.investment_debate_state.judge_decision}
              icon="👨‍⚖️"
            />
          )}
          
          {state.investment_debate_state.bull_history && (
            <Section
              title="Bull Case"
              content={state.investment_debate_state.bull_history}
              icon="🐂"
            />
          )}
          
          {state.investment_debate_state.bear_history && (
            <Section
              title="Bear Case"
              content={state.investment_debate_state.bear_history}
              icon="🐻"
            />
          )}
        </div>
      )}
      
      {/* Analyst Reports */}
      <div className="space-y-2">
        <h3 className="text-xs font-semibold text-text-secondary uppercase tracking-wide">Analyst Reports</h3>
        
        {state.market_report && (
          <Section
            title="Market Analysis"
            content={state.market_report}
            icon="📊"
          />
        )}
        
        {state.fundamentals_report && (
          <Section
            title="Fundamentals Analysis"
            content={state.fundamentals_report}
            icon="📈"
          />
        )}
        
        {(state.sentiment_report || state.information_report) && (
          <Section
            title="Sentiment & Information Analysis"
            content={state.sentiment_report || state.information_report}
            icon="💬"
          />
        )}
        
        {state.news_report && state.news_report !== state.sentiment_report && (
          <Section
            title="News Analysis"
            content={state.news_report}
            icon="📰"
          />
        )}
      </div>
    </div>
  );
}
