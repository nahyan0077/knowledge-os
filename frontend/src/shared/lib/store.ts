import { create } from 'zustand';
import { User, Organization, Project } from '../types';

interface AuthState {
  accessToken: string | null;
  user: User | null;
  organization: Organization | null;
  isAuthenticated: boolean;
  login: (accessToken: string, user: User, organization: Organization | null) => void;
  logout: () => void;
  setOrganization: (organization: Organization) => void;
  setAccessToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>((set) => {
  // Initialize from localStorage on client side
  const getInitialState = () => {
    if (typeof window === 'undefined') {
      return {
        accessToken: null,
        user: null,
        organization: null,
        isAuthenticated: false,
      };
    }
    const accessToken = localStorage.getItem('knowledge_os_access_token');
    const userJson = localStorage.getItem('knowledge_os_user');
    const orgJson = localStorage.getItem('knowledge_os_org');
    
    return {
      accessToken,
      user: userJson ? JSON.parse(userJson) : null,
      organization: orgJson ? JSON.parse(orgJson) : null,
      isAuthenticated: !!accessToken,
    };
  };

  const initialState = getInitialState();

  return {
    ...initialState,
    login: (accessToken, user, organization) => {
      localStorage.setItem('knowledge_os_access_token', accessToken);
      localStorage.setItem('knowledge_os_user', JSON.stringify(user));
      if (organization) {
        localStorage.setItem('knowledge_os_org', JSON.stringify(organization));
      } else {
        localStorage.removeItem('knowledge_os_org');
      }
      set({ accessToken, user, organization, isAuthenticated: true });
    },
    logout: () => {
      localStorage.removeItem('knowledge_os_access_token');
      localStorage.removeItem('knowledge_os_user');
      localStorage.removeItem('knowledge_os_org');
      set({ accessToken: null, user: null, organization: null, isAuthenticated: false });
    },
    setOrganization: (organization) => {
      localStorage.setItem('knowledge_os_org', JSON.stringify(organization));
      set({ organization });
    },
    setAccessToken: (accessToken) => {
      localStorage.setItem('knowledge_os_access_token', accessToken);
      set({ accessToken });
    },
  };
});

interface UiState {
  activeProjectId: string | null;
  activeProject: Project | null;
  sidebarOpen: boolean;
  setActiveProject: (project: Project | null) => void;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
}

export const useUiStore = create<UiState>((set) => {
  const getInitialProjectId = () => {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem('knowledge_os_active_project_id');
  };

  return {
    activeProjectId: getInitialProjectId(),
    activeProject: null,
    sidebarOpen: true,
    setActiveProject: (project) => {
      if (project) {
        localStorage.setItem('knowledge_os_active_project_id', project.id);
        set({ activeProjectId: project.id, activeProject: project });
      } else {
        localStorage.removeItem('knowledge_os_active_project_id');
        set({ activeProjectId: null, activeProject: null });
      }
    },
    toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
    setSidebarOpen: (open) => set({ sidebarOpen: open }),
  };
});
