'use client';

import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore, useUiStore } from '@/shared/lib/store';
import { apiClient } from '@/shared/api/client';
import { Project } from '@/shared/types';
import { useParams, useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import {
  FolderOpen,
  FileText,
  MessageSquare,
  Settings as SettingsIcon,
  ChevronLeft,
  ChevronRight,
  LayoutGrid,
  Menu,
  X,
  LogOut,
} from 'lucide-react';

interface ProjectLayoutProps {
  children: React.ReactNode;
}

export default function ProjectLayout({ children }: ProjectLayoutProps) {
  const params = useParams();
  const router = useRouter();
  const pathname = usePathname();
  const projectId = params?.projectId as string;

  const { organization, logout, user } = useAuthStore();
  const { activeProject, setActiveProject, sidebarOpen, toggleSidebar } = useUiStore();

  const { data: projectData, error } = useQuery<Project>({
    queryKey: ['project', projectId],
    queryFn: () => apiClient<Project>(`/projects/${projectId}`),
    enabled: !!projectId && (!activeProject || activeProject.id !== projectId),
  });

  useEffect(() => {
    if (projectData) {
      setActiveProject(projectData);
    }
  }, [projectData, setActiveProject]);

  useEffect(() => {
    if (error) {
      // If we can't find or access this project, redirect to dashboard
      router.replace('/dashboard');
    }
  }, [error, router]);

  const navItems = [
    {
      name: 'Documents',
      href: `/projects/${projectId}/documents`,
      icon: FileText,
    },
    {
      name: 'Conversations',
      href: `/projects/${projectId}/conversations`,
      icon: MessageSquare,
      // Matches subpaths like conversations/[id]
      match: (path: string) => path.includes('/conversations'),
    },
    {
      name: 'Settings',
      href: `/projects/${projectId}/settings`,
      icon: SettingsIcon,
    },
  ];

  const handleLogout = () => {
    logout();
    router.replace('/login');
  };

  const projectTitle = activeProject?.name || projectData?.name || 'Workspace';

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-100 overflow-hidden">
      {/* Sidebar Panel */}
      <aside
        className={`bg-zinc-900 border-r border-zinc-800 flex flex-col transition-all duration-300 z-30 shrink-0 ${
          sidebarOpen ? 'w-64' : 'w-16'
        }`}
      >
        {/* Sidebar Header */}
        <div className="p-4 border-b border-zinc-800/80 flex items-center justify-between min-h-[65px]">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="h-8 w-8 rounded-lg bg-gradient-to-tr from-indigo-500 to-purple-600 flex items-center justify-center font-bold text-white shrink-0">
              Ω
            </div>
            {sidebarOpen && (
              <span className="font-extrabold text-sm tracking-wide text-zinc-100 uppercase truncate">
                Knowledge OS
              </span>
            )}
          </div>
          {sidebarOpen && (
            <button
              onClick={toggleSidebar}
              className="text-zinc-500 hover:text-zinc-300 p-1 rounded-lg hover:bg-zinc-800/60 transition-all cursor-pointer"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Project Context Selector */}
        <div className="p-3 border-b border-zinc-850 flex items-center gap-2 overflow-hidden min-h-[57px]">
          <Link
            href="/dashboard"
            className="flex items-center justify-center h-8 w-8 rounded-lg bg-zinc-950 border border-zinc-800 text-zinc-400 hover:text-white shrink-0 transition-colors"
            title="All Projects"
          >
            <LayoutGrid className="h-4 w-4" />
          </Link>
          {sidebarOpen && (
            <div className="flex flex-col text-left truncate flex-1 pl-1">
              <span className="text-xs font-bold text-zinc-200 truncate">{projectTitle}</span>
              <span className="text-[10px] text-zinc-500 font-semibold uppercase tracking-wider">
                Active Project
              </span>
            </div>
          )}
        </div>

        {/* Navigation Section */}
        <nav className="flex-1 px-2 py-4 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = item.match ? item.match(pathname) : pathname === item.href;
            
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group ${
                  isActive
                    ? 'bg-indigo-600/15 border-l-2 border-indigo-500 text-indigo-400 font-semibold'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'
                }`}
              >
                <Icon
                  className={`h-5 w-5 shrink-0 transition-all group-hover:scale-105 ${
                    isActive ? 'text-indigo-400' : 'text-zinc-500 group-hover:text-zinc-400'
                  }`}
                />
                {sidebarOpen && <span className="truncate">{item.name}</span>}
              </Link>
            );
          })}
        </nav>

        {/* Sidebar Footer */}
        <div className="p-3 border-t border-zinc-800/80 flex flex-col gap-2 bg-zinc-900/40">
          {!sidebarOpen && (
            <button
              onClick={toggleSidebar}
              className="flex items-center justify-center w-10 h-10 rounded-lg hover:bg-zinc-800 text-zinc-400 hover:text-zinc-200 transition-colors cursor-pointer"
            >
              <ChevronRight className="h-5 w-5" />
            </button>
          )}

          {sidebarOpen && (
            <>
              <div className="flex items-center gap-2.5 px-2 py-1 overflow-hidden">
                <div className="h-8 w-8 rounded-full bg-zinc-850 flex items-center justify-center font-bold text-indigo-400 text-sm border border-zinc-800 shrink-0">
                  {user?.displayName ? user.displayName[0].toUpperCase() : 'U'}
                </div>
                <div className="flex flex-col text-left truncate">
                  <span className="text-xs font-semibold text-zinc-200 truncate">{user?.displayName}</span>
                  <span className="text-[10px] text-zinc-500 truncate">{user?.email}</span>
                </div>
              </div>
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/50 text-xs font-semibold border border-transparent hover:border-zinc-850 transition-all cursor-pointer"
              >
                <LogOut className="h-4 w-4 shrink-0" />
                <span>Logout Session</span>
              </button>
            </>
          )}
        </div>
      </aside>

      {/* Main Page Area */}
      <div className="flex-1 flex flex-col min-w-0 bg-zinc-950 relative overflow-hidden">
        {/* Mobile Navbar Header */}
        <header className="border-b border-zinc-900 bg-zinc-950/40 backdrop-blur-md px-6 py-4 flex items-center justify-between md:hidden sticky top-0 z-20 min-h-[65px]">
          <div className="flex items-center gap-3">
            <button
              onClick={toggleSidebar}
              className="p-1 rounded-lg text-zinc-400 hover:bg-zinc-900 border border-zinc-800 cursor-pointer"
            >
              <Menu className="h-5 w-5" />
            </button>
            <h2 className="font-bold text-sm text-zinc-200 truncate max-w-[150px]">{projectTitle}</h2>
          </div>
          <Link
            href="/dashboard"
            className="flex items-center justify-center h-8 w-8 rounded-lg bg-zinc-900 border border-zinc-800 text-zinc-400 hover:text-white"
          >
            <LayoutGrid className="h-4 w-4" />
          </Link>
        </header>

        {/* Content Wrapper */}
        <main className="flex-1 overflow-y-auto relative z-10 flex flex-col min-h-0">
          {children}
        </main>
      </div>
    </div>
  );
}
