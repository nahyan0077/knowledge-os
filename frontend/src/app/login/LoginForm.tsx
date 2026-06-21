import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { LogIn } from 'lucide-react';

const loginSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  password: z.string().min(1, 'Password is required'),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

interface LoginFormProps {
  onSubmit: (data: LoginFormValues) => Promise<void>;
  isLoading: boolean;
}

export function LoginForm({ onSubmit, isLoading }: LoginFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
          Email Address
        </label>
        <input
          type="email"
          {...register('email')}
          className="w-full px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
          placeholder="name@company.com"
          disabled={isLoading}
        />
        {errors.email && (
          <p className="mt-1 text-xs text-red-400">{errors.email.message}</p>
        )}
      </div>

      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400">
            Password
          </label>
        </div>
        <input
          type="password"
          {...register('password')}
          className="w-full px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
          placeholder="••••••••••••"
          disabled={isLoading}
        />
        {errors.password && (
          <p className="mt-1 text-xs text-red-400">{errors.password.message}</p>
        )}
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="w-full flex items-center justify-center gap-2 py-3 px-4 rounded-xl bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-indigo-600 hover:to-purple-700 text-white font-medium shadow-lg shadow-indigo-500/20 hover:shadow-indigo-500/30 transition-all active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
      >
        {isLoading ? (
          <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent"></div>
        ) : (
          <>
            <LogIn className="h-5 w-5" />
            <span>Sign In</span>
          </>
        )}
      </button>
    </form>
  );
}
