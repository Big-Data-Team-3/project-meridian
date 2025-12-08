import { type ReactElement } from 'react';
import { cn } from '@/lib/utils';

interface ContainerProps {
  children: React.ReactNode;
  className?: string;
}

export function Container({ children, className }: ContainerProps): ReactElement {
  return (
    <div
      className={cn(
        'max-w-[768px] w-full mx-auto',
        'px-4 sm:px-6 lg:px-10',
        className
      )}
    >
      {children}
    </div>
  );
}

