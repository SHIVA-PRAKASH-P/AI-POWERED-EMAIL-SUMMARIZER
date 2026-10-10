import {
  DashboardData,
  EmailSummary,
  EmailDetail,
  ActionItem,
  Meeting,
  DeadlineItem,
  CategoryCount,
  AnalysisResponse,
  AssertionVerification
} from '../types';

const BASE_URL = '/api';
const SESSION_STORAGE_KEY = 'summarizer_session_token';
const ACTIVE_EMAIL_KEY = 'summarizer_active_user_email';

export function getSessionToken(): string | null {
  try {
    return localStorage.getItem(SESSION_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setSessionToken(token: string | null): void {
  try {
    if (token) {
      localStorage.setItem(SESSION_STORAGE_KEY, token);
    } else {
      localStorage.removeItem(SESSION_STORAGE_KEY);
    }
  } catch {
    // ignore local storage restrictions
  }
}

export function getActiveUserEmail(): string {
  try {
    return localStorage.getItem(ACTIVE_EMAIL_KEY) || 'mock.faculty@university.edu';
  } catch {
    return 'mock.faculty@university.edu';
  }
}

export function setActiveUserEmail(email: string): void {
  try {
    localStorage.setItem(ACTIVE_EMAIL_KEY, email);
  } catch {
    // ignore
  }
}

let isRefreshingSession = false;

async function apiFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const token = getSessionToken();
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  let res = await fetch(input, {
    ...init,
    headers
  });

  // Self-healing recovery: if 401 Unauthorized (e.g. server restarted or token expired),
  // re-establish session for the active user email and retry once.
  if (res.status === 401 && !isRefreshingSession) {
    const urlStr = typeof input === 'string' ? input : input instanceof URL ? input.toString() : (input as Request).url;
    if (!urlStr.includes('/auth/switch-session') && !urlStr.includes('/auth/logout')) {
      isRefreshingSession = true;
      try {
        const activeEmail = getActiveUserEmail();
        const refreshRes = await fetch(`${BASE_URL}/auth/switch-session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: activeEmail })
        });
        if (refreshRes.ok) {
          const refreshData = await refreshRes.json();
          if (refreshData && refreshData.session_token) {
            setSessionToken(refreshData.session_token);
            setActiveUserEmail(refreshData.user.email);
            const retryHeaders = new Headers(init?.headers);
            retryHeaders.set('Authorization', `Bearer ${refreshData.session_token}`);
            res = await fetch(input, {
              ...init,
              headers: retryHeaders
            });
          }
        } else {
          // If session recreation fails for this email, clear token so default fallback user can serve
          setSessionToken(null);
          const fallbackHeaders = new Headers(init?.headers);
          fallbackHeaders.delete('Authorization');
          res = await fetch(input, {
            ...init,
            headers: fallbackHeaders
          });
        }
      } catch {
        // let original response stand on network errors
      } finally {
        isRefreshingSession = false;
      }
    }
  }

  return res;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let errorDetail = `Request failed with status ${res.status}`;
    try {
      const errJson = await res.json();
      if (errJson && errJson.detail) {
        errorDetail = errJson.detail;
      }
    } catch {
      // ignore parse error
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  // Session & User Switching (Stage 19B)
  getSessionToken,
  setSessionToken,
  getActiveUserEmail,
  setActiveUserEmail,

  async getCurrentUser(): Promise<{ id: number; email: string; name: string; role: string; provider_type: string }> {
    const res = await apiFetch(`${BASE_URL}/auth/me`);
    return handleResponse(res);
  },

  async getRegisteredUsers(): Promise<Array<{ id: number; email: string; name: string; role: string; provider_type: string }>> {
    const res = await apiFetch(`${BASE_URL}/auth/users`);
    return handleResponse(res);
  },

  async switchSession(email: string): Promise<{ session_token: string; user: { id: number; email: string; name: string; role: string; provider_type: string } }> {
    const res = await fetch(`${BASE_URL}/auth/switch-session`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email })
    });
    const data = await handleResponse<{ session_token: string; user: any }>(res);
    setSessionToken(data.session_token);
    setActiveUserEmail(data.user.email);
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('auth-session-changed', { detail: { email: data.user.email, user: data.user } }));
    }
    return data;
  },

  async logout(): Promise<{ status: string }> {
    const res = await apiFetch(`${BASE_URL}/auth/logout`, { method: 'POST' });
    setSessionToken(null);
    return handleResponse(res);
  },

  // Dashboard Metrics & Operational Feeds
  async getDashboard(): Promise<DashboardData> {
    const res = await apiFetch(`${BASE_URL}/dashboard`);
    return handleResponse<DashboardData>(res);
  },

  // Emails list with multi-parametric filtering
  async getEmails(params?: {
    search?: string;
    category?: string;
    priority?: string;
    is_read?: boolean;
    has_deadline?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<EmailSummary[]> {
    const query = new URLSearchParams();
    if (params) {
      if (params.search) query.append('search', params.search);
      if (params.category && params.category !== 'ALL') query.append('category', params.category);
      if (params.priority && params.priority !== 'ALL') query.append('priority', params.priority);
      if (params.is_read !== undefined) query.append('is_read', String(params.is_read));
      if (params.has_deadline !== undefined) query.append('has_deadline', String(params.has_deadline));
      if (params.skip !== undefined) query.append('skip', String(params.skip));
      if (params.limit !== undefined) query.append('limit', String(params.limit));
    }
    const res = await apiFetch(`${BASE_URL}/emails?${query.toString()}`);
    return handleResponse<EmailSummary[]>(res);
  },

  // Single Email Detail with AI intelligence, actions, meetings, entities
  async getEmailById(id: number): Promise<EmailDetail> {
    const res = await apiFetch(`${BASE_URL}/emails/${id}`);
    return handleResponse<EmailDetail>(res);
  },

  // Mark email as read
  async markEmailAsRead(id: number): Promise<EmailDetail> {
    const res = await apiFetch(`${BASE_URL}/emails/${id}/read`, {
      method: 'PATCH'
    });
    return handleResponse<EmailDetail>(res);
  },

  // Trigger Multi-Agent AI Analysis
  async analyzeEmail(id: number, forceRefresh: boolean = false): Promise<AnalysisResponse> {
    const res = await apiFetch(`${BASE_URL}/emails/${id}/analyze?force_refresh=${forceRefresh}`, {
      method: 'POST'
    });
    return handleResponse<AnalysisResponse>(res);
  },

  // Action Items
  async getActionItems(params?: {
    completed?: boolean;
    priority?: string;
    relationship_type?: string;
  }): Promise<ActionItem[]> {
    const query = new URLSearchParams();
    if (params) {
      if (params.completed !== undefined) query.append('completed', String(params.completed));
      if (params.priority && params.priority !== 'ALL') query.append('priority', params.priority);
      if (params.relationship_type && params.relationship_type !== 'ALL') {
        query.append('relationship_type', params.relationship_type);
      }
    }
    const res = await apiFetch(`${BASE_URL}/action-items?${query.toString()}`);
    return handleResponse<ActionItem[]>(res);
  },

  // Update Action Item (e.g. toggle completion)
  async updateActionItem(id: number, data: Partial<ActionItem>): Promise<ActionItem> {
    const res = await apiFetch(`${BASE_URL}/action-items/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    return handleResponse<ActionItem>(res);
  },

  // Upcoming Deadlines
  async getDeadlines(status: 'all' | 'pending' | 'completed' = 'all'): Promise<DeadlineItem[]> {
    const res = await apiFetch(`${BASE_URL}/deadlines?status=${status}`);
    return handleResponse<DeadlineItem[]>(res);
  },

  // Upcoming Meetings
  async getMeetings(): Promise<Meeting[]> {
    const res = await apiFetch(`${BASE_URL}/meetings`);
    return handleResponse<Meeting[]>(res);
  },

  // Search across emails
  async searchEmails(q: string, category?: string, priority?: string): Promise<EmailSummary[]> {
    const query = new URLSearchParams({ q });
    if (category && category !== 'ALL') query.append('category', category);
    if (priority && priority !== 'ALL') query.append('priority', priority);
    const res = await apiFetch(`${BASE_URL}/search?${query.toString()}`);
    return handleResponse<EmailSummary[]>(res);
  },

  // Distinct categories with email counts
  async getCategories(): Promise<CategoryCount[]> {
    const res = await apiFetch(`${BASE_URL}/categories`);
    return handleResponse<CategoryCount[]>(res);
  },

  // Audit and verify arbitrary assertion against email
  async verifyAssertion(payload: {
    field_name: string;
    extracted_value: string;
    email_id?: number;
    raw_text?: string;
  }): Promise<AssertionVerification> {
    const res = await apiFetch(`${BASE_URL}/analysis/verify-assertion`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    return handleResponse<AssertionVerification>(res);
  },

  // Backend Database Integrity & Counts
  async getDbStatus(): Promise<{
    status: string;
    counts: {
      emails: number;
      analyses: number;
      action_items: number;
      meetings: number;
      evidences: number;
      entities: number;
    };
  }> {
    const res = await apiFetch(`${BASE_URL}/db-status`);
    return handleResponse(res);
  },

  // Backend Health & Mode Check
  async getHealth(): Promise<{
    status: string;
    ai_mode: string;
    stage: string;
    email_provider?: string;
  }> {
    const res = await apiFetch(`${BASE_URL}/health`);
    return handleResponse(res);
  },

  // Email Provider Status
  async getEmailProviderStatus(): Promise<import('../types').EmailProviderStatus> {
    const res = await apiFetch(`${BASE_URL}/email-provider/status`);
    return handleResponse<import('../types').EmailProviderStatus>(res);
  },

  // Trigger Email Ingestion Sync
  async syncEmails(limit: number = 15, provider?: string): Promise<import('../types').EmailSyncResult> {
    const params = new URLSearchParams();
    if (limit) params.append('limit', String(limit));
    if (provider) params.append('provider', provider);
    const res = await apiFetch(`${BASE_URL}/email-provider/sync?${params.toString()}`, {
      method: 'POST'
    });
    return handleResponse<import('../types').EmailSyncResult>(res);
  },

  // Cross-Email Intelligence (Stage 14)
  async getCrossEmailIntelligence(emailId: number): Promise<{ success: boolean; data: import('../types').CrossEmailIntelligence }> {
    const res = await apiFetch(`${BASE_URL}/emails/${emailId}/cross-intelligence`);
    return handleResponse(res);
  },

  // Global Inbox Topic Clusters
  async getTopicClusters(): Promise<{ success: boolean; total_clusters: number; clusters: import('../types').TopicCluster[] }> {
    const res = await apiFetch(`${BASE_URL}/cross-intelligence/clusters`);
    return handleResponse(res);
  },

  // Faculty Personalization & Preferences (Stage 15)
  async getPreferences(): Promise<import('../types').FacultyPreference> {
    const res = await apiFetch(`${BASE_URL}/preferences`);
    return handleResponse<import('../types').FacultyPreference>(res);
  },

  async updatePreferences(updates: import('../types').FacultyPreferenceUpdate): Promise<import('../types').FacultyPreference> {
    const res = await apiFetch(`${BASE_URL}/preferences`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });
    return handleResponse<import('../types').FacultyPreference>(res);
  },

  async resetPreferences(): Promise<import('../types').FacultyPreference> {
    const res = await apiFetch(`${BASE_URL}/preferences/reset`, {
      method: 'POST'
    });
    return handleResponse<import('../types').FacultyPreference>(res);
  },

  // Google OAuth 2.0 & Gmail Connection (Stage 19A & Multi-Account)
  async getGmailConnectUrl(forceNew: boolean = true): Promise<{ status: string; authorization_url: string; state: string; target_account: string; scope: string }> {
    const query = forceNew ? '?force_new=true' : '';
    const res = await apiFetch(`${BASE_URL}/email-provider/gmail/connect${query}`);
    return handleResponse(res);
  },

  async getGmailOAuthStatus(): Promise<import('../types').GmailOAuthStatus> {
    const res = await apiFetch(`${BASE_URL}/email-provider/gmail/status`);
    return handleResponse<import('../types').GmailOAuthStatus>(res);
  },

  async disconnectGmail(): Promise<{ status: string; message: string }> {
    const res = await apiFetch(`${BASE_URL}/email-provider/gmail/disconnect`, {
      method: 'POST'
    });
    return handleResponse<{ status: string; message: string }>(res);
  },

  // Synchronize Latest College Gmail Emails (Stage 19C)
  async syncGmailEmails(limit: number = 60): Promise<{
    success: boolean;
    message: string;
    data: {
      fetched: number;
      imported: number;
      skipped_duplicates: number;
      failed: number;
      user_id: number;
      target_account: string;
      provider: string;
    };
  }> {
    const params = new URLSearchParams();
    if (limit) params.append('limit', String(limit));
    const res = await apiFetch(`${BASE_URL}/email-provider/gmail/sync?${params.toString()}`, {
      method: 'POST'
    });
    return handleResponse(res);
  }
};

