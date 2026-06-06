'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useAuthStore, useUiStore } from '@/shared/lib/store';
import { apiClient } from '@/shared/api/client';
import { Project, ProjectListResponse } from '@/shared/types';
import { useRouter } from 'next/navigation';
import { Plus, LogOut, Folder, FileText, MessageSquare, Settings as SettingsIcon, Calendar, ArrowRight, X } from 'lucide-react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

const projectSchema = z.object({
  name: z.string().min(1, 'Project name is required').max(160, 'Name cannot exceed 160 characters'),
  description: z.string().max(4000, 'Description cannot exceed 4000 characters').optional(),
});

type ProjectFormValues = z.infer<typeof projectSchema>;

export default function DashboardPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { user, organization, logout } = useAuthStore();
  const { setActiveProject } = useUiStore();
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const { register, handleSubmit, formState: { errors }, reset } = useForm<ProjectFormValues>({
    resolver: zodResolver(projectSchema),
  });

  const { data, isLoading, error } = useQuery<ProjectListResponse>({
    queryKey: ['projects', organization?.id],
    queryFn: () => apiClient<ProjectListResponse>('/projects', {
      params: { organization_id: organization?.id },
    }),
    enabled: !!organization?.id,
  });

  const createMutation = useMutation({
    mutationFn: (values: ProjectFormValues) => apiClient<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify({
        organization_id: organization?.id,
        name: values.name,
        description: values.description || null,
      }),
    }),
    onSuccess: (newProject) => {
      queryClient.invalidateQueries({ queryKey: ['projects', organization?.id] });
      setIsModalOpen(false);
      reset();
      setActiveProject(newProject);
      router.push(`/projects/${newProject.id}/documents`);
    },
    onError: (err: any) => {
      setCreateError(err.message || 'Failed to create project');
    },
  });

  const onSubmit = (data: ProjectFormValues) => {
    setCreateError(null);
    createMutation.mutate(data);
  };

  const handleProjectSelect = (project: Project) => {
    setActiveProject(project);
    router.push(`/projects/${project.id}/documents`);
  };

  const handleLogout = () => {
    logout();
    router.push('/login');
  };

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100 flex flex-col relative overflow-hidden">
      {/* Background Blurs */}
      <div className="absolute top-0 right-1/4 w-[500px] h-[500px] rounded-full bg-indigo-500/5 blur-[150px] pointer-events-none"></div>
      <div className="absolute bottom-0 left-1/4 w-[500px] h-[500px] rounded-full bg-purple-500/5 blur-[150px] pointer-events-none"></div>

      {/* Header */}
      <header className="border-b border-zinc-900 bg-zinc-950/50 backdrop-blur-md sticky top-0 z-40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shadow-md shadow-indigo-500/25">
            Ω
          </div>
          <div>
            <h1 className="font-bold text-lg leading-tight bg-gradient-to-r from-white to-zinc-400 bg-clip-text">Knowledge OS</h1>
            <p className="text-xs text-zinc-500 font-medium">{organization?.name || 'Personal Workspace'}</p>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-semibold text-zinc-200">{user?.displayName}</p>
            <p className="text-xs text-zinc-500">{user?.email}</p>
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-2 rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 text-sm font-medium border border-zinc-800/80 transition-all cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline">Logout</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-6xl w-full mx-auto px-6 py-10 flex flex-col">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-white sm:text-3xl">Projects</h2>
            <p className="text-sm text-zinc-400 mt-1">Select an existing workspace or initialize a new project.</p>
          </div>
          <button
            onClick={() => {
              setCreateError(null);
              setIsModalOpen(true);
            }}
            className="flex items-center gap-2 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium shadow-lg shadow-indigo-500/10 hover:shadow-indigo-500/20 transition-all cursor-pointer active:scale-95"
          >
            <Plus className="h-4 w-4" />
            <span>New Project</span>
          </button>
        </div>

        {isLoading ? (
          <div className="flex-1 flex items-center justify-center py-20">
            <div className="flex flex-col items-center gap-4">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
              <p className="text-zinc-500 text-sm">Loading projects...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex-1 py-16 flex items-center justify-center">
            <div className="max-w-md text-center p-8 rounded-2xl bg-zinc-900/40 border border-zinc-800">
              <p className="text-red-400 text-sm font-medium">Failed to load projects</p>
              <p className="text-zinc-500 text-xs mt-2">{(error as any).message || 'An error occurred.'}</p>
            </div>
          </div>
        ) : !data || data.items.length === 0 ? (
          <div className="flex-1 py-20 flex flex-col items-center justify-center border border-dashed border-zinc-800 rounded-3xl bg-zinc-900/10 backdrop-blur-sm">
            <div className="h-12 w-12 rounded-2xl bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-4">
              <Folder className="h-6 w-6 text-zinc-600" />
            </div>
            <h3 className="text-lg font-bold text-zinc-300">No projects yet</h3>
            <p className="text-zinc-500 text-sm max-w-xs text-center mt-2">
              Get started by creating your first project workspace to upload documents and query knowledge.
            </p>
            <button
              onClick={() => setIsModalOpen(true)}
              className="mt-6 flex items-center gap-2 py-2 px-4 rounded-xl bg-zinc-900 hover:bg-zinc-850 text-zinc-300 border border-zinc-800 transition-all cursor-pointer hover:border-zinc-700"
            >
              <Plus className="h-4 w-4" />
              <span>Create Project</span>
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {data.items.map((project) => (
              <div
                key={project.id}
                onClick={() => handleProjectSelect(project)}
                className="group relative flex flex-col justify-between p-6 rounded-2xl bg-zinc-900/40 hover:bg-zinc-900/80 border border-zinc-900 hover:border-zinc-800/80 transition-all duration-300 shadow-lg cursor-pointer overflow-hidden hover:-translate-y-0.5"
              >
                {/* Glow border on hover */}
                <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"></div>
                
                <div>
                  <div className="h-10 w-10 rounded-xl bg-zinc-950 border border-zinc-800/80 flex items-center justify-center mb-4 group-hover:scale-105 transition-transform duration-300">
                    <Folder className="h-5 w-5 text-indigo-400" />
                  </div>
                  <h3 className="text-lg font-bold text-white group-hover:text-indigo-400 transition-colors line-clamp-1">{project.name}</h3>
                  <p className="text-zinc-400 text-xs mt-2 line-clamp-3 leading-relaxed min-h-[4rem]">{project.description || 'No description provided.'}</p>
                </div>

                <div className="border-t border-zinc-900/80 mt-6 pt-4 flex items-center justify-between text-zinc-500 text-xs">
                  <div className="flex items-center gap-1.5 font-medium">
                    <Calendar className="h-3.5 w-3.5" />
                    <span>{new Date(project.created_at).toLocaleDateString()}</span>
                  </div>
                  <div className="flex items-center gap-1 font-semibold text-indigo-400 opacity-0 group-hover:opacity-100 transition-all translate-x-2 group-hover:translate-x-0">
                    <span>Enter</span>
                    <ArrowRight className="h-3 w-3" />
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </main>

      {/* Create Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl max-w-md w-full p-6 shadow-2xl relative animate-in scale-in duration-200">
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-4 right-4 text-zinc-400 hover:text-zinc-200 rounded-lg p-1 transition-colors cursor-pointer"
            >
              <X className="h-5 w-5" />
            </button>

            <h3 className="text-xl font-bold text-white">Create New Project</h3>
            <p className="text-xs text-zinc-400 mt-1">Initialize a workspace to start uploading files.</p>

            {createError && (
              <div className="mt-4 p-3 rounded-lg bg-red-950/40 border border-red-950 text-red-200 text-xs">
                {createError}
              </div>
            )}

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 mt-6">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                  Project Name
                </label>
                <input
                  type="text"
                  {...register('name')}
                  className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all text-sm"
                  placeholder="e.g., Knowledge Base RAG"
                  disabled={createMutation.isPending}
                />
                {errors.name && (
                  <p className="mt-1 text-xs text-red-400">{errors.name.message}</p>
                )}
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2">
                  Description
                </label>
                <textarea
                  {...register('description')}
                  rows={4}
                  className="w-full px-4 py-2.5 rounded-xl bg-zinc-950 border border-zinc-800 text-white placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all text-sm resize-none"
                  placeholder="What is the purpose of this project?"
                  disabled={createMutation.isPending}
                />
                {errors.description && (
                  <p className="mt-1 text-xs text-red-400">{errors.description.message}</p>
                )}
              </div>

              <div className="flex gap-3 justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 text-sm font-medium text-zinc-400 hover:text-zinc-200 bg-zinc-950 hover:bg-zinc-850 border border-zinc-800 rounded-xl transition-all cursor-pointer"
                  disabled={createMutation.isPending}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-500 rounded-xl transition-all shadow-lg shadow-indigo-500/10 cursor-pointer active:scale-95"
                  disabled={createMutation.isPending}
                >
                  {createMutation.isPending ? 'Creating...' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
