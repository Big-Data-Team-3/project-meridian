'use client';

import { type ReactElement } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { Button } from '@/components/ui/Button';
import { cn } from '@/lib/utils';

interface HeaderProps {
  className?: string;
}

export function Header({ className }: HeaderProps): ReactElement {
  const { user, logout, isLoading } = useAuth();

  const handleLogout = async (): Promise<void> => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  return (
    <header
      className={cn(
        'fixed top-0 left-0 right-0 h-[60px]',
        'bg-bg-primary border-b border-border',
        'flex items-center justify-between px-4 z-50',
        className
      )}
    >
      <div className="flex items-center gap-4">
        <h1 className="text-lg font-semibold text-text-primary">Meridian</h1>
      </div>
      <div className="flex items-center gap-3">
        <ThemeToggle />
        {user && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-text-secondary hidden sm:inline">
              {user.email}
            </span>
            <Button
              variant="ghost"
              size="sm"
              onClick={handleLogout}
              disabled={isLoading}
            >
              Logout
            </Button>
          </div>
        )}
      </div>
    </header>
  );
}

