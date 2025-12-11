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
  const decisionColors = {
    BUY: 'bg-green-500/20 text-green-600 border-green-500/30',
    SELL: 'bg-red-500/20 text-red-600 border-red-500/30',
    HOLD: 'bg-yellow-500/20 text-yellow-600 border-yellow-500/30',
  };
  
  const decisionColor = decisionColors[decision as keyof typeof decisionColors] || 'bg-surface text-text-primary border-border';
  
  return (
    <div className="space-y-3 mt-4">
      {/* Decision Badge */}
      <div className="flex items-center justify-between">
        <div className={cn('inline-flex items-center gap-2 px-4 py-2 rounded-lg border font-semibold', decisionColor)}>
          <span className="text-lg">
            {decision === 'BUY' && '📈'}
            {decision === 'SELL' && '📉'}
            {decision === 'HOLD' && '⏸️'}
          </span>
          <span>Decision: {decision}</span>
        </div>
        <div className="text-xs text-text-secondary">
          {company} • {date}
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
