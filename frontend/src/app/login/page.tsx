'use client';

import React, { useState, useEffect } from 'react';
import { useAuthStore } from '@/shared/lib/store';
import { apiClient } from '@/shared/api/client';
import { AuthResponse } from '@/shared/types';
import { ShieldAlert, CheckCircle2 } from 'lucide-react';
import { LoginForm, LoginFormValues } from './LoginForm';
import { RegisterForm, RegisterFormValues } from './RegisterForm';
import { GoogleSandboxModal } from './GoogleSandboxModal';

interface GoogleGsiCallbackResponse {
  credential?: string;
}

interface GoogleGsiConfig {
  client_id: string;
  callback: (response: GoogleGsiCallbackResponse) => void;
}

interface GoogleGsiRenderButtonOptions {
  theme?: 'outline' | 'filled_blue' | 'filled_black';
  size?: 'small' | 'medium' | 'large';
  text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
  shape?: 'rectangular' | 'pill' | 'circle' | 'square';
  layout?: 'logo_only' | 'text_only';
  logo_alignment?: 'left' | 'center';
  width?: number;
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: GoogleGsiConfig) => void;
          prompt: () => void;
          renderButton: (
            element: HTMLElement | null,
            options: GoogleGsiRenderButtonOptions
          ) => void;
        };
      };
    };
  }
}

export default function LoginPage() {
  const [isRegister, setIsRegister] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [showGoogleMock, setShowGoogleMock] = useState(false);
  const [googleScriptLoaded, setGoogleScriptLoaded] = useState(false);
  
  const login = useAuthStore((state) => state.login);

  useEffect(() => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId) return;

    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => {
      setGoogleScriptLoaded(true);
    };
    document.body.appendChild(script);

    return () => {
      if (document.body.contains(script)) {
        document.body.removeChild(script);
      }
    };
  }, []);

  useEffect(() => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId || !googleScriptLoaded || typeof window === 'undefined' || !window.google) return;

    try {
      window.google.accounts.id.initialize({
        client_id: clientId,
        callback: (response) => {
          if (response.credential) {
            onGoogleLogin(response.credential);
          }
        },
      });

      const btnContainer = document.getElementById('google-official-btn');
      if (btnContainer) {
        window.google.accounts.id.renderButton(btnContainer, {
          theme: 'filled_black',
          size: 'large',
          text: 'continue_with',
          shape: 'rectangular',
          width: 384,
        });
      }
    } catch (err) {
      console.error('Google GSI initialization error:', err);
    }
  }, [googleScriptLoaded]);

  const onGoogleLogin = async (idToken: string) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await apiClient<AuthResponse>('/auth/google', {
        method: 'POST',
        body: JSON.stringify({ id_token: idToken }),
        skipAuth: true,
      });

      const user = {
        id: res.user.id,
        email: res.user.email,
        displayName: res.user.display_name,
      };

      const org = res.organization ? {
        id: res.organization.id,
        name: res.organization.name,
        slug: res.organization.slug,
        type: res.organization.type,
      } : null;

      login(res.access_token, user, org);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Google authentication failed.';
      setErrorMsg(msg);
    } finally {
      setIsLoading(false);
      setShowGoogleMock(false);
    }
  };

  const handleGoogleClick = () => {
    const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID;
    if (!clientId) {
      setShowGoogleMock(true);
      return;
    }

    if (typeof window !== 'undefined') {
      if (!window.google) {
        setErrorMsg('Google Sign-In SDK is loading. Please try again.');
        return;
      }

      try {
        window.google.accounts.id.prompt();
      } catch (err) {
        console.error('Google One Tap error:', err);
        setErrorMsg('Failed to initialize Google One Tap.');
      }
    }
  };

  const onLogin = async (data: LoginFormValues) => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const res = await apiClient<AuthResponse>('/auth/login', {
        method: 'POST',
        body: JSON.stringify(data),
        skipAuth: true,
      });

      const user = {
        id: res.user.id,
        email: res.user.email,
        displayName: res.user.display_name,
      };

      const org = res.organization ? {
        id: res.organization.id,
        name: res.organization.name,
        slug: res.organization.slug,
        type: res.organization.type,
      } : null;

      login(res.access_token, user, org);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Login failed. Please verify credentials.';
      setErrorMsg(msg);
    } finally {
      setIsLoading(false);
    }
  };

  const onRegister = async (data: RegisterFormValues) => {
    setIsLoading(true);
    setErrorMsg(null);
    setSuccessMsg(null);
    try {
      const res = await apiClient<AuthResponse>('/auth/register', {
        method: 'POST',
        body: JSON.stringify({
          email: data.email,
          display_name: data.displayName,
          password: data.password,
        }),
        skipAuth: true,
      });

      setSuccessMsg('Account created successfully! Logging you in...');
      
      setTimeout(() => {
        const user = {
          id: res.user.id,
          email: res.user.email,
          displayName: res.user.display_name,
        };

        const org = res.organization ? {
          id: res.organization.id,
          name: res.organization.name,
          slug: res.organization.slug,
          type: res.organization.type,
        } : null;

        login(res.access_token, user, org);
      }, 1500);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Registration failed. Try a different email.';
      setErrorMsg(msg);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-zinc-950 px-4 py-12 sm:px-6 lg:px-8 relative overflow-hidden">
      {/* Background Gradients */}
      <div className="absolute top-1/4 left-1/4 -translate-x-1/2 -translate-y-1/2 w-96 h-96 rounded-full bg-indigo-500/10 blur-[120px] pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 translate-x-1/2 translate-y-1/2 w-96 h-96 rounded-full bg-purple-500/10 blur-[120px] pointer-events-none"></div>

      <div className="w-full max-w-md space-y-8 relative z-10">
        <div className="flex flex-col items-center">
          <div className="flex items-center justify-center h-12 w-12 rounded-xl bg-gradient-to-tr from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/30">
            <span className="text-xl font-black text-white">Ω</span>
          </div>
          <h2 className="mt-6 text-center text-3xl font-extrabold tracking-tight text-white bg-clip-text">
            Knowledge OS
          </h2>
          <p className="mt-2 text-center text-sm text-zinc-400">
            {isRegister ? 'Create an account to get started' : 'Sign in to access your projects'}
          </p>
        </div>

        <div className="bg-zinc-900/60 backdrop-blur-xl border border-zinc-800/80 rounded-2xl p-8 shadow-2xl shadow-black/50">
          {errorMsg && (
            <div className="mb-6 p-4 rounded-xl bg-red-950/40 border border-red-900/50 text-red-200 text-sm flex items-start gap-3 animate-in fade-in slide-in-from-top-2 duration-300">
              <ShieldAlert className="h-5 w-5 text-red-400 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-6 p-4 rounded-xl bg-emerald-950/40 border border-emerald-900/50 text-emerald-200 text-sm flex items-start gap-3 animate-in fade-in slide-in-from-top-2 duration-300">
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Continue with Google button */}
          <div className="relative w-full mb-6">
            <button
              type="button"
              onClick={handleGoogleClick}
              disabled={isLoading}
              className="w-full flex items-center justify-center gap-3 py-3 px-4 rounded-xl bg-zinc-950 border border-zinc-800 hover:bg-zinc-850 hover:border-zinc-700 text-zinc-100 font-semibold transition-all active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
            >
              {/* Google G icon */}
              <svg className="h-5 w-5 shrink-0" viewBox="0 0 24 24" fill="currentColor">
                <path
                  d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  fill="#4285F4"
                />
                <path
                  d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  fill="#34A853"
                />
                <path
                  d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
                  fill="#FBBC05"
                />
                <path
                  d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
                  fill="#EA4335"
                />
              </svg>
              <span>Continue with Google</span>
            </button>

            {process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID && (
              <div
                id="google-official-btn"
                className={`absolute inset-0 opacity-[0.01] overflow-hidden ${
                  isLoading ? 'pointer-events-none' : 'cursor-pointer'
                } [&_*]:!w-full [&_*]:!h-full [&_*]:!max-w-none [&_*]:!max-h-none [&_*]:!min-h-0 [&_*]:!min-w-0`}
              ></div>
            )}
          </div>

          <div className="flex items-center gap-3 my-4">
            <div className="h-[1px] bg-zinc-800/80 flex-1"></div>
            <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest">Or login with</span>
            <div className="h-[1px] bg-zinc-800/80 flex-1"></div>
          </div>

          {!isRegister ? (
            <LoginForm onSubmit={onLogin} isLoading={isLoading} />
          ) : (
            <RegisterForm onSubmit={onRegister} isLoading={isLoading} />
          )}

          <div className="mt-6 text-center">
            <button
              onClick={() => {
                setIsRegister(!isRegister);
                setErrorMsg(null);
                setSuccessMsg(null);
              }}
              className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
            >
              {isRegister ? 'Already have an account? Sign In' : "Don't have an account? Sign Up"}
            </button>
          </div>
        </div>
      </div>

      <GoogleSandboxModal
        isOpen={showGoogleMock}
        onClose={() => setShowGoogleMock(false)}
        onSimulate={onGoogleLogin}
      />
    </div>
  );
}
