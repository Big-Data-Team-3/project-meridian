'use client';

import { type ReactElement } from 'react';
import { cn } from '@/lib/utils';

interface AgentIconProps {
  agentName: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

const AGENT_ICONS: Record<string, string> = {
  'Market Analyst': '📈',
  'Fundamentals Analyst': '📊',
  'Information Analyst': '📰',
  'Bull Researcher': '🐂',
  'Bear Researcher': '🐻',
  'Research Manager': '👔',
  'Trader': '💼',
  'Risky Analyst': '⚡',
  'Safe Analyst': '🛡️',
  'Neutral Analyst': '⚖️',
  'Risk Manager': '🎯',
};

const AGENT_COLORS: Record<string, string> = {
  'Market Analyst': 'bg-blue-500',
  'Fundamentals Analyst': 'bg-green-500',
  'Information Analyst': 'bg-purple-500',
  'Bull Researcher': 'bg-green-600',
  'Bear Researcher': 'bg-red-600',
  'Research Manager': 'bg-indigo-500',
  'Trader': 'bg-yellow-500',
  'Risky Analyst': 'bg-orange-500',
  'Safe Analyst': 'bg-teal-500',
  'Neutral Analyst': 'bg-gray-500',
  'Risk Manager': 'bg-pink-500',
};

const SIZE_CLASSES = {
  sm: 'w-6 h-6 text-xs',
  md: 'w-8 h-8 text-sm',
  lg: 'w-12 h-12 text-base',
};

export function AgentIcon({ agentName, size = 'md', className }: AgentIconProps): ReactElement {
  const icon = AGENT_ICONS[agentName] || '🤖';
  const colorClass = AGENT_COLORS[agentName] || 'bg-gray-500';
  const sizeClass = SIZE_CLASSES[size];

  return (
    <div
      className={cn(
        'flex items-center justify-center rounded-full',
        colorClass,
        sizeClass,
        className
      )}
      title={agentName}
    >
      <span>{icon}</span>
    </div>
  );
}

