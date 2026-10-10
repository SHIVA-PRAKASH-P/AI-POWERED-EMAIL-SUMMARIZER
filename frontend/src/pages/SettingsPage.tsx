import React, { useState, useEffect } from 'react';
import {
  Cpu,
  User,
  Sliders,
  CheckCircle2,
  Database,
  RotateCw,
  AlertTriangle,
  Server,
  Mail,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  RotateCcw,
  ExternalLink,
  Lock,
  LogOut,
  XCircle
} from 'lucide-react';
import { api } from '../services/api';
import { EmailProviderStatus, GmailOAuthStatus } from '../types';

export const SettingsPage: React.FC = () => {
  // Stage 19A Google OAuth State
  const [gmailOAuth, setGmailOAuth] = useState<GmailOAuthStatus | null>(null);
  const [oauthLoading, setOauthLoading] = useState(false);
  const [oauthBanner, setOauthBanner] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  // Stage 19C Gmail Sync State
  const [gmailSyncLoading, setGmailSyncLoading] = useState(false);
  const [gmailSyncResult, setGmailSyncResult] = useState<{
    success: boolean;
    message: string;
    data?: any;
  } | null>(null);

  // Faculty Profile & Personalization State
  const [facultyName, setFacultyName] = useState('Dr. Faculty');
  const [role, setRole] = useState('Professor & Academic Incharge');
  const [dept, setDept] = useState('Computer Science & Engineering');
  const [priorityMode, setPriorityMode] = useState('BALANCED');
  const [highCategories, setHighCategories] = useState('Examination,Academic');
  const [customKeywordsHigh, setCustomKeywordsHigh] = useState('marks,question paper,naac,accreditation,urgent');
  const [customKeywordsLow, setCustomKeywordsLow] = useState('newsletter,invitation,webinar,sports');
  const [deadlineUrgencyDays, setDeadlineUrgencyDays] = useState(3);
  const [authorityWeight, setAuthorityWeight] = useState(1.0);
  const [deadlineWeight, setDeadlineWeight] = useState(1.0);

  const [engineMode, setEngineMode] = useState<'mock' | 'llm'>('mock');
  const [savedMessage, setSavedMessage] = useState(false);
  const [savingPref, setSavingPref] = useState(false);

  // Live Database & System Telemetry
  const [dbStatus, setDbStatus] = useState<any>(null);
  const [healthStatus, setHealthStatus] = useState<any>(null);
  const [providerStatus, setProviderStatus] = useState<EmailProviderStatus | null>(null);
  const [dbLoading, setDbLoading] = useState(true);
  const [dbError, setDbError] = useState<string | null>(null);

  // Email Ingestion Sync state
  const [syncLoading, setSyncLoading] = useState(false);
  const [syncResultMsg, setSyncResultMsg] = useState<string | null>(null);

  const loadPreferences = async () => {
    try {
      const pref = await api.getPreferences();
      if (pref) {
        setFacultyName(pref.faculty_name || 'Dr. Faculty');
        setRole(pref.role || 'Professor & Academic Incharge');
        setDept(pref.department || 'Computer Science & Engineering');
        setPriorityMode(pref.priority_mode || 'BALANCED');
        setHighCategories(pref.high_priority_categories || 'Examination,Academic');
        setCustomKeywordsHigh(pref.custom_keywords_high || 'marks,question paper,naac,accreditation,urgent');
        setCustomKeywordsLow(pref.custom_keywords_low || 'newsletter,invitation,webinar,sports');
        setDeadlineUrgencyDays(pref.deadline_urgency_days || 3);
        setAuthorityWeight(pref.authority_weight || 1.0);
        setDeadlineWeight(pref.deadline_weight || 1.0);
      }
    } catch (err) {
      console.error('Failed to load faculty preferences:', err);
    }
  };

  const loadSystemStatus = async () => {
    try {
      setDbLoading(true);
      setDbError(null);
      const [dbRes, healthRes, provRes] = await Promise.all([
        api.getDbStatus(),
        api.getHealth(),
        api.getEmailProviderStatus()
      ]);
      setDbStatus(dbRes);
      setHealthStatus(healthRes);
      setProviderStatus(provRes);
    } catch (err: any) {
      console.error('Failed to load system status:', err);
      setDbError(err.message || 'Unable to connect to backend service');
    } finally {
      setDbLoading(false);
    }
  };

  const handleSyncIngestion = async () => {
    try {
      setSyncLoading(true);
      setSyncResultMsg(null);
      const res = await api.syncEmails(15);
      setSyncResultMsg(`Synced ${res.data.imported} new, ${res.data.skipped} existing via ${res.data.provider}`);
      await loadSystemStatus();
      setTimeout(() => setSyncResultMsg(null), 5000);
    } catch (err: any) {
      setSyncResultMsg(`Sync error: ${err.message}`);
    } finally {
      setSyncLoading(false);
    }
  };

  const loadGmailOAuthStatus = async () => {
    try {
      const res = await api.getGmailOAuthStatus();
      setGmailOAuth(res);
    } catch (e) {
      console.error('Failed to load Gmail OAuth status:', e);
    }
  };

  const handleConnectGmail = async () => {
    try {
      setOauthLoading(true);
      const res = await api.getGmailConnectUrl();
      if (res && res.authorization_url) {
        window.location.href = res.authorization_url;
      }
    } catch (err: any) {
      setOauthBanner({
        type: 'error',
        message: err.message || 'Google OAuth is not configured. Please define GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env.'
      });
      setOauthLoading(false);
    }
  };

  const handleDisconnectGmail = async () => {
    if (!confirm('Are you sure you want to disconnect your college Gmail account?')) return;
    try {
      setOauthLoading(true);
      await api.disconnectGmail();
      await loadGmailOAuthStatus();
      await loadSystemStatus();
      setOauthBanner({
        type: 'success',
        message: 'College Gmail account disconnected successfully.'
      });
    } catch (err: any) {
      setOauthBanner({ type: 'error', message: err.message || 'Failed to disconnect.' });
    } finally {
      setOauthLoading(false);
    }
  };

  const handleSyncGmail = async () => {
    try {
      setGmailSyncLoading(true);
      setGmailSyncResult(null);
      const res = await api.syncGmailEmails(60);
      setGmailSyncResult({
        success: true,
        message: `Synced ${res.data.imported} new, ${res.data.skipped_duplicates} duplicate(s) skipped from College Gmail (Total fetched: ${res.data.fetched}).`,
        data: res.data
      });
      await loadSystemStatus();
    } catch (err: any) {
      setGmailSyncResult({
        success: false,
        message: `Gmail sync failed: ${err.message || 'Unknown error'}`
      });
    } finally {
      setGmailSyncLoading(false);
    }
  };

  useEffect(() => {
    loadPreferences();
    loadSystemStatus();
    loadGmailOAuthStatus();

    // Check query params for OAuth feedback
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get('oauth') === 'success') {
      const email = urlParams.get('email') || 'your Gmail account';
      setOauthBanner({
        type: 'success',
        message: `Successfully connected and verified Gmail account: ${email}`
      });
      window.history.replaceState({}, document.title, window.location.pathname);
      loadGmailOAuthStatus();
      loadSystemStatus();
      window.dispatchEvent(new CustomEvent('auth-session-changed'));
    } else if (urlParams.get('oauth') === 'error') {
      const reason = urlParams.get('reason');
      const attempted = urlParams.get('attempted');
      let msg = 'Google OAuth connection failed.';
      if (reason === 'wrong_account') {
        msg = `Unauthorized account (${attempted || 'unknown'}). Please authenticate using a valid Google account.`;
      } else if (reason === 'denied') {
        msg = 'OAuth authorization was cancelled or denied.';
      } else if (reason === 'token_exchange_failed') {
        msg = 'Failed to exchange authorization code with Google.';
      } else if (reason === 'verification_failed') {
        msg = 'Failed to verify account identity with Gmail API.';
      }
      setOauthBanner({ type: 'error', message: msg });
      window.history.replaceState({}, document.title, window.location.pathname);
    }
  }, []);

  const handleSavePreferences = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSavingPref(true);
      await api.updatePreferences({
        faculty_name: facultyName,
        role,
        department: dept,
        priority_mode: priorityMode,
        high_priority_categories: highCategories,
        custom_keywords_high: customKeywordsHigh,
        custom_keywords_low: customKeywordsLow,
        deadline_urgency_days: Number(deadlineUrgencyDays),
        authority_weight: Number(authorityWeight),
        deadline_weight: Number(deadlineWeight)
      });
      // Also cache in local storage for instant offline UI sync
      localStorage.setItem('faculty_role', role);
      localStorage.setItem('faculty_dept', dept);
      setSavedMessage(true);
      setTimeout(() => setSavedMessage(false), 4000);
    } catch (err: any) {
      alert(`Failed to save preferences: ${err.message}`);
    } finally {
      setSavingPref(false);
    }
  };

  const handleResetPreferences = async () => {
    if (!window.confirm('Reset all personalization settings to default balanced values?')) return;
    try {
      const reset = await api.resetPreferences();
      setFacultyName(reset.faculty_name);
      setRole(reset.role);
      setDept(reset.department);
      setPriorityMode(reset.priority_mode);
      setHighCategories(reset.high_priority_categories);
      setCustomKeywordsHigh(reset.custom_keywords_high);
      setCustomKeywordsLow(reset.custom_keywords_low);
      setDeadlineUrgencyDays(reset.deadline_urgency_days);
      setAuthorityWeight(reset.authority_weight);
      setDeadlineWeight(reset.deadline_weight);
      setSavedMessage(true);
      setTimeout(() => setSavedMessage(false), 3000);
    } catch (err: any) {
      alert(`Failed to reset preferences: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Faculty Personalization &amp; System Settings</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Configure individual academic roles, personalized priority heuristics, focus categories, and model providers.
        </p>
      </div>

      {savedMessage && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-center space-x-2 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
          <span>Personalization preferences stored in database. Future email analyses will reflect these criteria.</span>
        </div>
      )}

      {oauthBanner && (
        <div
          className={`p-3 border text-xs rounded-lg flex items-center justify-between space-x-2 animate-fadeIn ${
            oauthBanner.type === 'success'
              ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
              : 'bg-rose-50 border-rose-200 text-rose-800'
          }`}
        >
          <div className="flex items-center space-x-2">
            {oauthBanner.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            ) : (
              <XCircle className="w-4 h-4 text-rose-600 flex-shrink-0" />
            )}
            <span>{oauthBanner.message}</span>
          </div>
          <button
            onClick={() => setOauthBanner(null)}
            className="text-xs opacity-60 hover:opacity-100 font-bold px-1"
          >
            &times;
          </button>
        </div>
      )}

      {/* Profile & Personalization Form (Stage 15) */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <User className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-semibold text-slate-900">Faculty Identity &amp; Priority Tuning Profile</h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-50 text-purple-700 border border-purple-200">
            Stage 15 Personalization
          </span>
        </div>

        <form onSubmit={handleSavePreferences} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700">Faculty Name</label>
              <input
                type="text"
                value={facultyName}
                onChange={(e) => setFacultyName(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700">Institutional Designation</label>
              <input
                type="text"
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700">Department</label>
              <input
                type="text"
                value={dept}
                onChange={(e) => setDept(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2 border-t border-slate-100">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700">Priority Tuning Preset</label>
              <select
                value={priorityMode}
                onChange={(e) => setPriorityMode(e.target.value)}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500"
              >
                <option value="BALANCED">Balanced Academic (Multi-Factor Standard)</option>
                <option value="DEADLINE_HEAVY">Deadline-Heavy (Amplifies Approaching Dates)</option>
                <option value="AUTHORITY_FIRST">Authority-First (Deans &amp; COE Directives Highest)</option>
                <option value="CUSTOM">Custom Multiplier Weights</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700">Deadline Urgency Horizon (Days)</label>
              <input
                type="number"
                min={1}
                max={14}
                value={deadlineUrgencyDays}
                onChange={(e) => setDeadlineUrgencyDays(Number(e.target.value))}
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500"
              />
              <p className="text-[10px] text-slate-400">Deadlines within this number of days are flagged as Immediate Urgency.</p>
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700">High-Priority Focus Categories (Comma-separated)</label>
            <input
              type="text"
              value={highCategories}
              onChange={(e) => setHighCategories(e.target.value)}
              placeholder="e.g. Examination, Academic, Research"
              className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500"
            />
            <p className="text-[10px] text-slate-400">Communications in these categories receive a +2.5 personalized priority boost.</p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700">Custom High Urgency Keywords</label>
              <input
                type="text"
                value={customKeywordsHigh}
                onChange={(e) => setCustomKeywordsHigh(e.target.value)}
                placeholder="e.g. marks, accreditation, naac, question paper"
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500"
              />
              <p className="text-[10px] text-slate-400">Emails mentioning these terms receive priority elevation.</p>
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-slate-700">Custom Low Priority Demotion Keywords</label>
              <input
                type="text"
                value={customKeywordsLow}
                onChange={(e) => setCustomKeywordsLow(e.target.value)}
                placeholder="e.g. newsletter, webinar, invitation, sports"
                className="w-full px-3 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 focus:outline-none focus:border-indigo-500"
              />
              <p className="text-[10px] text-slate-400">Routine emails with these terms are demoted unless mandatory.</p>
            </div>
          </div>

          <div className="flex items-center justify-between pt-3">
            <button
              type="button"
              onClick={handleResetPreferences}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs text-slate-600 hover:text-slate-900 border border-slate-200 hover:bg-slate-50 rounded-lg transition-all"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset Defaults</span>
            </button>

            <button
              type="submit"
              disabled={savingPref}
              className="inline-flex items-center space-x-1.5 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>{savingPref ? 'Saving Settings...' : 'Save Personalized Preferences'}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Backend & Database Telemetry */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <Database className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-semibold text-slate-900">Backend Database Telemetry &amp; Entity Counts</h3>
          </div>
          <button
            onClick={loadSystemStatus}
            disabled={dbLoading}
            className="text-xs text-slate-500 hover:text-slate-800 flex items-center space-x-1"
          >
            <RotateCw className={`w-3.5 h-3.5 ${dbLoading ? 'animate-spin text-indigo-600' : ''}`} />
            <span>Refresh Telemetry</span>
          </button>
        </div>

        {dbLoading ? (
          <div className="p-8 text-center text-xs text-slate-400">Querying backend database statistics...</div>
        ) : dbError ? (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700 flex items-start space-x-2">
            <AlertTriangle className="w-4 h-4 text-rose-600 mt-0.5 flex-shrink-0" />
            <div>
              <p className="font-semibold">Backend Disconnected</p>
              <p className="text-[11px] mt-0.5">{dbError}</p>
            </div>
          </div>
        ) : dbStatus ? (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-3">
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                <span className="w-2 h-2 rounded-full bg-emerald-500 mr-1.5 animate-pulse" />
                Backend: {healthStatus?.status || dbStatus.status}
              </span>
              <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-200">
                <Server className="w-3.5 h-3.5 mr-1 text-indigo-600" />
                Engine: {healthStatus?.ai_mode || 'MOCK'}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                Stage: {healthStatus?.stage || 'Integrated'}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 pt-2">
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
                <span className="text-lg font-bold text-slate-800 block">{dbStatus.counts.emails}</span>
                <span className="text-[11px] text-slate-500 font-medium">Emails</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
                <span className="text-lg font-bold text-slate-800 block">{dbStatus.counts.analyses}</span>
                <span className="text-[11px] text-slate-500 font-medium">AI Analyses</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
                <span className="text-lg font-bold text-slate-800 block">{dbStatus.counts.action_items}</span>
                <span className="text-[11px] text-slate-500 font-medium">Action Items</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
                <span className="text-lg font-bold text-slate-800 block">{dbStatus.counts.meetings}</span>
                <span className="text-[11px] text-slate-500 font-medium">Meetings</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
                <span className="text-lg font-bold text-slate-800 block">{dbStatus.counts.evidences}</span>
                <span className="text-[11px] text-slate-500 font-medium">Evidences</span>
              </div>
              <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-center">
                <span className="text-lg font-bold text-slate-800 block">{dbStatus.counts.entities}</span>
                <span className="text-[11px] text-slate-500 font-medium">Entities</span>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      {/* AI Engine Provider Architecture */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <Cpu className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-semibold text-slate-900">AI Intelligence Engine Provider</h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
            Dual-Engine System
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div
            onClick={() => setEngineMode('mock')}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              engineMode === 'mock'
                ? 'bg-indigo-50/50 border-indigo-500 ring-2 ring-indigo-500/10'
                : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900">Deterministic Mock Engine</span>
              {engineMode === 'mock' && <CheckCircle2 className="w-4 h-4 text-indigo-600" />}
            </div>
            <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
              Zero-dependency deterministic offline simulation. 100% uptime with zero external LLM API quota requirements.
            </p>
          </div>

          <div
            onClick={() => setEngineMode('llm')}
            className={`p-4 rounded-xl border cursor-pointer transition-all ${
              engineMode === 'llm'
                ? 'bg-indigo-50/50 border-indigo-500 ring-2 ring-indigo-500/10'
                : 'bg-white border-slate-200 hover:border-slate-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold text-slate-900">Live Generative LLM Adapter</span>
              {engineMode === 'llm' && <CheckCircle2 className="w-4 h-4 text-indigo-600" />}
            </div>
            <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
              Connects to external LLM providers (Gemini / OpenAI / Anthropic) with deterministic fallback protection.
            </p>
          </div>
        </div>
      </div>

      {/* Email Ingestion Provider Architecture */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-2">
            <Mail className="w-4 h-4 text-indigo-600" />
            <h3 className="text-sm font-semibold text-slate-900">Email Ingestion Provider Architecture</h3>
          </div>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">
            Stage 13 Modular
          </span>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-4 bg-slate-50 p-4 rounded-xl border border-slate-200">
          <div className="space-y-1">
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-slate-900 uppercase">
                Active Provider: {providerStatus?.active_provider || 'MOCK'}
              </span>
              {providerStatus?.is_authenticated ? (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                  <ShieldCheck className="w-3 h-3 mr-1" />
                  Ready &amp; Ingesting
                </span>
              ) : (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-100 text-amber-800">
                  Unauthenticated
                </span>
              )}
              {providerStatus?.fallback_active && (
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-indigo-100 text-indigo-800">
                  Fallback Protection Active
                </span>
              )}
            </div>
            <p className="text-[11px] text-slate-500">
              Configured: <code className="text-slate-700 font-mono font-semibold">{providerStatus?.configured_provider || 'mock'}</code> &bull; Gmail API Credentials: {providerStatus?.gmail_configured ? 'Configured' : 'Not Provided (Offline Mode)'}
            </p>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={handleSyncIngestion}
              disabled={syncLoading}
              className="inline-flex items-center space-x-1.5 px-3.5 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${syncLoading ? 'animate-spin' : ''}`} />
              <span>{syncLoading ? 'Ingesting...' : 'Sync Ingestion'}</span>
            </button>
          </div>
        </div>

        {/* Stage 19A: College Gmail OAuth Connection */}
        <div className="p-4 bg-white rounded-xl border border-slate-200 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Mail className="w-4 h-4 text-indigo-600" />
              <span className="text-xs font-bold text-slate-900">College Gmail Connection (Stage 19A)</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200">
                OAuth 2.0
              </span>
            </div>
            {gmailOAuth?.connected ? (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-100 text-emerald-800">
                <ShieldCheck className="w-3 h-3 mr-1" />
                Connected
              </span>
            ) : (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-slate-100 text-slate-700">
                Not Connected
              </span>
            )}
          </div>

          <div className="space-y-1 text-xs">
            <div className="flex items-center justify-between text-[11px] text-slate-600">
              <span>Connected Account:</span>
              <code className="font-mono font-bold text-slate-800">
                {gmailOAuth?.connected && gmailOAuth?.email ? gmailOAuth.email : 'No account connected'}
              </code>
            </div>
            <div className="flex items-center justify-between text-[11px] text-slate-500">
              <span>Permission Scope:</span>
              <span className="font-mono text-[10px] bg-slate-100 px-1.5 py-0.5 rounded text-slate-700 flex items-center">
                <Lock className="w-2.5 h-2.5 mr-1 text-slate-500" />
                Read-Only (gmail.readonly)
              </span>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
            <p className="text-[11px] text-slate-500 max-w-sm">
              {gmailOAuth?.connected
                ? 'Your Gmail account is verified and ready for read-only access. You can sync messages or connect another Gmail account anytime.'
                : 'Connect your Gmail account via official Google OAuth 2.0. The connection requires minimum read-only permissions (gmail.readonly).'}
            </p>

            {gmailOAuth?.connected ? (
              <div className="flex flex-wrap items-center gap-2">
                <button
                  onClick={handleSyncGmail}
                  disabled={gmailSyncLoading || oauthLoading}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
                  title="Synchronize a controlled batch of latest 60 emails from Gmail (Stage 19C)"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${gmailSyncLoading ? 'animate-spin' : ''}`} />
                  <span>{gmailSyncLoading ? 'Syncing Gmail...' : 'Sync Latest 60 Gmail Emails'}</span>
                </button>
                <button
                  onClick={handleConnectGmail}
                  disabled={oauthLoading}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-50 hover:bg-indigo-100 border border-indigo-200 text-indigo-700 rounded-lg text-xs font-semibold shadow-sm transition-all"
                  title="Connect another Gmail account via official Google OAuth"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Connect another Gmail account</span>
                </button>
                <button
                  onClick={handleDisconnectGmail}
                  disabled={oauthLoading || gmailSyncLoading}
                  className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-rose-50 hover:bg-rose-100 border border-rose-200 text-rose-700 rounded-lg text-xs font-semibold shadow-sm transition-all"
                >
                  <LogOut className="w-3.5 h-3.5" />
                  <span>{oauthLoading ? 'Disconnecting...' : 'Disconnect'}</span>
                </button>
              </div>
            ) : (
              <button
                onClick={handleConnectGmail}
                disabled={oauthLoading}
                className="inline-flex items-center space-x-1.5 px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-indigo-300 text-white rounded-lg text-xs font-semibold shadow-sm transition-all"
              >
                <ExternalLink className="w-3.5 h-3.5" />
                <span>{oauthLoading ? 'Connecting...' : 'Connect Gmail'}</span>
              </button>
            )}
          </div>

          {gmailSyncResult && (
            <div className={`p-3 rounded-lg flex items-start space-x-2 text-xs border ${
              gmailSyncResult.success
                ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                : 'bg-rose-50 border-rose-200 text-rose-800'
            }`}>
              {gmailSyncResult.success ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0 mt-0.5" />
              ) : (
                <AlertTriangle className="w-4 h-4 text-rose-600 flex-shrink-0 mt-0.5" />
              )}
              <div className="flex-1">
                <p className="font-semibold">{gmailSyncResult.message}</p>
                {gmailSyncResult.data && (
                  <p className="text-[11px] opacity-90 mt-0.5">
                    Imported: <strong>{gmailSyncResult.data.imported}</strong> &bull; Duplicates Skipped: <strong>{gmailSyncResult.data.skipped_duplicates}</strong> &bull; Failed: <strong>{gmailSyncResult.data.failed}</strong> &bull; User ID: <strong>{gmailSyncResult.data.user_id}</strong>
                  </p>
                )}
              </div>
            </div>
          )}
        </div>

        {syncResultMsg && (
          <div className="p-3 bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs rounded-lg flex items-center space-x-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />
            <span>{syncResultMsg}</span>
          </div>
        )}
      </div>

      {/* Priority Engine Mathematical Factor Transparency */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
        <div className="flex items-center space-x-2 pb-3 border-b border-slate-100">
          <Sliders className="w-4 h-4 text-indigo-600" />
          <h3 className="text-sm font-semibold text-slate-900">Priority Engine Multi-Factor Weights &amp; Personalization</h3>
        </div>

        <p className="text-xs text-slate-500 leading-relaxed">
          The patent-oriented priority engine synthesizes 9 orthogonal dimensions calibrated with your personalized profile weights and focus categories.
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-700 block">Personalized Category Focus</span>
            <span className="text-[11px] text-slate-500">{highCategories || 'None'}</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-700 block">Immediate Deadline Horizon</span>
            <span className="text-[11px] text-slate-500">&le; {deadlineUrgencyDays} Days</span>
          </div>
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200">
            <span className="text-[11px] font-semibold text-slate-700 block">Priority Preset Tuning</span>
            <span className="text-[11px] text-slate-500">{priorityMode}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
