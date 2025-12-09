'use client';

import { useEffect, useRef, type ReactElement } from 'react';
import { Button } from '@/components/ui/Button';

interface GoogleSignInProps {
  onSuccess: (credential: string) => Promise<void>;
  onError?: (error: string) => void;
  disabled?: boolean;
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string }) => void;
          }) => void;
          renderButton: (element: HTMLElement, config: {
            theme: 'outline' | 'filled_blue' | 'filled_black';
            size: 'large' | 'medium' | 'small';
            text: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
            width?: number;
          }) => void;
          prompt: () => void;
        };
      };
    };
  }
}

export function GoogleSignIn({ onSuccess, onError, disabled }: GoogleSignInProps): ReactElement {
  const buttonRef = useRef<HTMLDivElement>(null);
  const scriptLoaded = useRef(false);

  useEffect(() => {
    // Load Google Identity Services script
    if (scriptLoaded.current) return;

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      scriptLoaded.current = true;
      initializeGoogleSignIn();
    };
    script.onerror = () => {
      if (onError) {
        onError('Failed to load Google Sign-In script');
      }
    };
    document.head.appendChild(script);

    return () => {
      // Cleanup if needed
    };
  }, []);

  const initializeGoogleSignIn = () => {
    if (!window.google || !buttonRef.current) return;

    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    
    if (!clientId) {
      console.error('NEXT_PUBLIC_GOOGLE_CLIENT_ID is not set');
      if (onError) {
        onError('Google Client ID not configured');
      }
      return;
    }

    try {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: async (response) => {
          console.log('🔵 Step 1: Google Sign-In callback received');
          console.log('   Credential length:', response.credential?.length || 0);
          try {
            console.log('🔵 Step 2: Calling onSuccess callback...');
            await onSuccess(response.credential);
            console.log('✅ Step 2: onSuccess completed successfully');
          } catch (error) {
            console.error('❌ Step 2: Error in onSuccess callback:', error);
            if (onError) {
              onError(error instanceof Error ? error.message : 'Authentication failed');
            }
          }
        },
      });

      // Render the button
      if (buttonRef.current) {
        window.google.accounts.id.renderButton(buttonRef.current, {
          theme: 'outline',
          size: 'large',
          text: 'signin_with',
          width: 300,
        });
      }
    } catch (error) {
      console.error('Error initializing Google Sign-In:', error);
      if (onError) {
        onError('Failed to initialize Google Sign-In');
      }
    }
  };

  // Re-initialize when button ref is ready
  useEffect(() => {
    if (scriptLoaded.current && buttonRef.current && window.google) {
      initializeGoogleSignIn();
    }
  }, [buttonRef.current]);

  if (!process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID) {
    return (
      <div className="text-error text-sm text-center">
        Google Sign-In is not configured. Please set NEXT_PUBLIC_GOOGLE_CLIENT_ID.
      </div>
    );
  }

  return (
    <div className="w-full">
      <div
        ref={buttonRef}
        className="flex justify-center"
        style={{ minHeight: '40px' }}
      />
      {disabled && (
        <div className="text-text-secondary text-xs text-center mt-2">
          Please wait...
        </div>
      )}
    </div>
  );
}

