'use client';

import { type ReactElement } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { AuthProvider } from '@/contexts/AuthContext';
import { ConversationProvider } from '@/contexts/ConversationContext';
import { AgentProvider } from '@/contexts/AgentContext';
import { useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }): ReactElement {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5 * 60 * 1000, // 5 minutes
            refetchOnWindowFocus: false,
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <AgentProvider>
          <ConversationProvider>{children}</ConversationProvider>
          </AgentProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}

