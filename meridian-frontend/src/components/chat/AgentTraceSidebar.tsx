'use client';

import { useEffect, useState, type ReactElement } from 'react';
import { cn } from '@/lib/utils';
import { useAgent } from '@/contexts/AgentContext';
import { AgentTraceTimeline } from './AgentTraceTimeline';

interface AgentTraceSidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AgentTraceSidebar({ isOpen, onClose }: AgentTraceSidebarProps): ReactElement {
  const { trace, currentActivity, agentAnalysis } = useAgent();
  const [isDownloading, setIsDownloading] = useState(false);

  // Close sidebar when Escape key is pressed
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      // Prevent body scroll when sidebar is open
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);

  const downloadPDF = async () => {
    if (!agentAnalysis) return;
    
    setIsDownloading(true);
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/agents/pdf`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(agentAnalysis),
      });
      
      if (!response.ok) {
        throw new Error('Failed to generate PDF');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Meridian_${agentAnalysis.company}_${agentAnalysis.date}.pdf`;
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

  if (!isOpen) {
    return <></>;
  }

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/50 z-50 lg:z-40"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed top-0 right-0 bottom-0 w-full sm:w-[480px] lg:w-[520px]',
          'bg-surface border-l border-border',
          'transform transition-transform duration-300 ease-in-out',
          'z-50 lg:z-40',
          'flex flex-col',
          'shadow-xl'
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-border bg-surface-secondary">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-text-primary">Agent Trace</h2>
            {currentActivity && (
              <div className="flex items-center gap-2 px-2 py-1 bg-surface-tertiary rounded-md">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
                <span className="text-xs text-text-secondary">Active</span>
              </div>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-surface-hover rounded-lg transition-colors"
            aria-label="Close trace sidebar"
          >
            <svg
              className="w-5 h-5 text-text-secondary"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4">
          {trace ? (
            <AgentTraceTimeline trace={trace} />
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="text-4xl mb-4">🤖</div>
              <p className="text-text-secondary mb-2">No agent trace available</p>
              <p className="text-sm text-text-secondary opacity-75">
                Agent activity will appear here when agents are active
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        {trace && trace.agentsCalled.length > 0 && (
          <div className="p-4 border-t border-border bg-surface-secondary space-y-3">
            {/* Agent count */}
            <div className="text-xs text-text-secondary mb-2">
              {trace.agentsCalled.length} agent{trace.agentsCalled.length !== 1 ? 's' : ''} involved in this analysis
            </div>
            
            {/* Agent badges */}
            <div className="flex flex-wrap gap-2">
              {trace.agentsCalled.map((agentName) => (
                <div
                  key={agentName}
                  className="flex items-center gap-1.5 px-2 py-1 bg-surface-tertiary rounded-md"
                >
                  <span className="text-xs text-text-primary">{agentName}</span>
                </div>
              ))}
            </div>
            
            {/* PDF Download Button */}
            {agentAnalysis && (
              <button
                onClick={downloadPDF}
                disabled={isDownloading}
                className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-accent hover:bg-accent-hover text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed font-medium"
              >
                {isDownloading ? (
                  <>
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <span>Generating PDF...</span>
                  </>
                ) : (
                  <>
                    <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span>Download Full Report (PDF)</span>
                  </>
                )}
              </button>
            )}
          </div>
        )}
      </aside>
    </>
  );
}

