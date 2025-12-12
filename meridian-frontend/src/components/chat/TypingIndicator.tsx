import { type ReactElement } from 'react';
import { cn } from '@/lib/utils';

export function TypingIndicator(): ReactElement {
  return (
    <div className="flex items-center gap-1 px-4 py-2">
      <div className="flex gap-1">
        <div
          className={cn(
            'w-2 h-2 rounded-full bg-text-secondary',
            'animate-bounce'
          )}
          style={{ animationDelay: '0ms' }}
        />
        <div
          className={cn(
            'w-2 h-2 rounded-full bg-text-secondary',
            'animate-bounce'
          )}
          style={{ animationDelay: '150ms' }}
        />
        <div
          className={cn(
            'w-2 h-2 rounded-full bg-text-secondary',
            'animate-bounce'
          )}
          style={{ animationDelay: '300ms' }}
        />
      </div>
    </div>
  );
}

