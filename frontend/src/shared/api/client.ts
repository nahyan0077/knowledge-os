import { useAuthStore } from '../lib/store';
import { ApiErrorDetail } from '../types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  info: ApiErrorDetail;
  status: number;

  constructor(message: string, info: ApiErrorDetail, status: number) {
    super(message);
    this.name = 'ApiError';
    this.info = info;
    this.status = status;
  }
}

interface RequestOptions extends RequestInit {
  params?: Record<string, string | number | boolean | undefined>;
  skipAuth?: boolean;
}

let isRefreshing = false;
let refreshSubscribers: ((token: string) => void)[] = [];

function subscribeTokenRefresh(cb: (token: string) => void) {
  refreshSubscribers.push(cb);
}

function onRefreshed(token: string) {
  refreshSubscribers.forEach((cb) => cb(token));
  refreshSubscribers = [];
}

export async function apiClient<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { params, skipAuth, ...init } = options;

  let url = `${API_BASE_URL}/api/v1${path}`;
  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined) {
        searchParams.append(key, String(val));
      }
    });
    const queryString = searchParams.toString();
    if (queryString) {
      url += `?${queryString}`;
    }
  }

  const headers = new Headers(init.headers);
  if (!skipAuth) {
    const token = useAuthStore.getState().accessToken;
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...init,
    headers,
  });

  if (response.status === 401 && !skipAuth && path !== '/auth/refresh') {
    if (isRefreshing) {
      return new Promise<T>((resolve, reject) => {
        subscribeTokenRefresh(async (newToken) => {
          try {
            headers.set('Authorization', `Bearer ${newToken}`);
            const res = await fetch(url, { ...init, headers });
            if (!res.ok) {
              reject(await parseError(res));
              return;
            }
            const data = res.status === 204 ? (null as T) : await res.json();
            resolve(data);
          } catch (err) {
            reject(err);
          }
        });
      });
    }

    isRefreshing = true;

    try {
      const refreshRes = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!refreshRes.ok) {
        // Refresh token failed/expired -> Log out
        useAuthStore.getState().logout();
        throw new Error('Session expired. Please log in again.');
      }

      const refreshData = await refreshRes.json();
      const newAccessToken = refreshData.access_token;
      
      const user = {
        id: refreshData.user.id,
        email: refreshData.user.email,
        displayName: refreshData.user.display_name,
      };
      
      const org = refreshData.organization ? {
        id: refreshData.organization.id,
        name: refreshData.organization.name,
        slug: refreshData.organization.slug,
        type: refreshData.organization.type,
      } : null;

      useAuthStore.getState().login(newAccessToken, user, org);
      isRefreshing = false;
      onRefreshed(newAccessToken);

      // Retry original request
      headers.set('Authorization', `Bearer ${newAccessToken}`);
      const retryResponse = await fetch(url, { ...init, headers });
      if (!retryResponse.ok) {
        throw await parseError(retryResponse);
      }
      return retryResponse.status === 204 ? (null as T) : await retryResponse.json();
    } catch (err) {
      isRefreshing = false;
      refreshSubscribers = [];
      useAuthStore.getState().logout();
      throw err;
    }
  }

  if (!response.ok) {
    throw await parseError(response);
  }

  if (response.status === 204) {
    return null as T;
  }

  return response.json();
}

async function parseError(response: Response): Promise<ApiError> {
  try {
    const errorJson = await response.json();
    const detail: ApiErrorDetail = {
      type: errorJson.type || 'error',
      title: errorJson.title || 'API Error',
      status: response.status,
      detail: errorJson.detail || 'An unexpected error occurred.',
      error_code: errorJson.error_code || 'api_error',
    };
    return new ApiError(detail.detail, detail, response.status);
  } catch {
    const detail: ApiErrorDetail = {
      type: 'error',
      title: 'HTTP Error',
      status: response.status,
      detail: response.statusText || 'An unexpected error occurred.',
      error_code: 'http_error',
    };
    return new ApiError(detail.detail, detail, response.status);
  }
}
