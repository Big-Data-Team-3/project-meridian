'use client';

import { useState, useEffect, type ReactElement } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/hooks/useAuth';
import { ThemeToggle } from '@/components/ui/ThemeToggle';
import { Container } from '@/components/layout/Container';
import { GoogleSignIn } from '@/components/auth/GoogleSignIn';

export default function Home(): ReactElement {
  const router = useRouter();
  const { isAuthenticated, isLoading: authLoading, loginWithGoogle } = useAuth();
  const [error, setError] = useState('');
  const [isGoogleLoading, setIsGoogleLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated && !authLoading) {
      router.push('/chat');
    }
  }, [isAuthenticated, authLoading, router]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-bg-primary">
        <div className="text-text-secondary">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-bg-primary flex flex-col">
      <div className="absolute top-4 right-4">
        <ThemeToggle />
      </div>

      <main className="flex-1 flex items-center justify-center px-4 py-16">
        <Container className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-semibold text-text-primary mb-2">
              Meridian
          </h1>
            <p className="text-text-secondary">
              Financial Intelligence Platform
          </p>
        </div>

          <div className="bg-surface border border-border rounded-xl p-6 shadow-sm">
            <div className="text-center mb-6">
              <h2 className="text-xl font-semibold text-text-primary mb-2">
                Sign in to continue
              </h2>
              <p className="text-sm text-text-secondary">
                Use your Google account to access Meridian
              </p>
            </div>

            {error && (
              <div className="mb-4 text-error text-sm text-center" role="alert">
                {error}
              </div>
            )}

            {/* Google Sign-In */}
            <div className="mt-4">
              <GoogleSignIn
                onSuccess={async (credential) => {
                  console.log('🔵 Step 0: Page - Google Sign-In onSuccess triggered');
                  setIsGoogleLoading(true);
                  setError('');
                  try {
                    await loginWithGoogle(credential);
                    console.log('✅ Step 9: Page - Authentication successful, redirecting to /chat');
                    router.push('/chat');
                  } catch (err) {
                    console.error('❌ Step 9: Page - Error during authentication:', err);
                    const errorMessage = err instanceof Error ? err.message : 'Google authentication failed';
                    setError(errorMessage);
                    console.error('   Error message displayed to user:', errorMessage);
                  } finally {
                    setIsGoogleLoading(false);
                  }
                }}
                onError={(errorMsg) => {
                  console.error('❌ Page - GoogleSignIn onError:', errorMsg);
                  setError(errorMsg);
                  setIsGoogleLoading(false);
                }}
                disabled={isGoogleLoading}
              />
            </div>
        </div>

          <p className="text-center text-text-secondary text-sm mt-6">
            Get started with financial analysis and insights
          </p>
        </Container>
      </main>
    </div>
  );
}
