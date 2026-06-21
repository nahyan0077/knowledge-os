import React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { UserPlus } from 'lucide-react';

const registerSchema = z.object({
  email: z.string().email('Please enter a valid email address'),
  displayName: z.string().min(2, 'Name must be at least 2 characters'),
  password: z.string().min(12, 'Password must be at least 12 characters'),
});

export type RegisterFormValues = z.infer<typeof registerSchema>;

interface RegisterFormProps {
  onSubmit: (data: RegisterFormValues) => Promise<void>;
  isLoading: boolean;
}

export function RegisterForm({ onSubmit, isLoading }: RegisterFormProps) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div>
        <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
          Full Name
        </label>
        <input
          type="text"
          {...register('displayName')}
          className="w-full px-4 py-3 rounded-xl bg-zinc-950 border border-zinc-800 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
          placeholder="John Doe"
          disabled={isLoading}
        />
        {errors.displayName && (
          <p className="mt-1 text-xs text-red-400">{errors.displayName.message}</p>
        )}
      </div>

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
        <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
          Password (min 12 chars)
        </label>
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
            <UserPlus className="h-5 w-5" />
            <span>Create Account</span>
          </>
        )}
      </button>
    </form>
  );
}
