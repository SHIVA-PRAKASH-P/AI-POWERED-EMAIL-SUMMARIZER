import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Mail,
  Inbox,
  AlertTriangle,
  Clock,
  Calendar,
  CheckSquare,
  ArrowRight,
  Sparkles,
  MapPin,
  CheckCircle2,
  Circle,
  ExternalLink,
  RefreshCw
} from 'lucide-react';
import { api } from '../services/api';
import { DashboardData } from '../types';
import {
  formatDate,
  formatRelativeTime,
  getPriorityBadge,
  getCategoryBadge,
  getRelationshipBadge,
  getDeadlineStatusBadge
} from '../utils/formatters';

export const DashboardPage: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const navigate = useNavigate();

  const isSyncingRef = useRef(false);
  const hasAutoSyncedRef = useRef(false);

  const loadDashboard = async (showLoadingState: boolean = true) => {
    try {
      if (showLoadingState) setLoading(true);
      setError(null);
      const [res, user] = await Promise.all([
        api.getDashboard(),
        api.getCurrentUser().catch(() => null)
      ]);
      setData(res);
      if (user) setCurrentUser(user);
    } catch (err: any) {
      setError(err.message || 'Failed to load dashboard metrics');
    } finally {
      if (showLoadingState) setLoading(false);
    }
  };

  const triggerAutoSyncIfEligible = async () => {
    if (hasAutoSyncedRef.current || isSyncingRef.current) return;
    hasAutoSyncedRef.current = true;

    try {
      // Check authenticated user profile: only provider_type === 'gmail' is eligible for Gmail sync
      const activeUser = await api.getCurrentUser();
      if (activeUser?.provider_type !== 'gmail') {
        return;
      }

      isSyncingRef.current = true;
      setSyncStatus('Syncing latest emails...');

      try {
        await api.syncGmailEmails(60);
        setSyncStatus('Inbox updated');
        // Refresh dashboard data once after sync
        await loadDashboard(false);
        setTimeout(() => {
          setSyncStatus(null);
        }, 4000);
      } catch (syncErr: any) {
        // If sync fails or Gmail is disconnected, silently preserve existing dashboard
        console.log('Background auto-sync skipped (Gmail disconnected or unavailable):', syncErr?.message || syncErr);
        setSyncStatus(null);
      }
    } catch (userErr) {
      console.warn('Failed to verify user eligibility for auto-sync:', userErr);
    } finally {
      isSyncingRef.current = false;
    }
  };

  useEffect(() => {
    hasAutoSyncedRef.current = false;
    loadDashboard(true);
    triggerAutoSyncIfEligible();

    const handleRefresh = () => {
      hasAutoSyncedRef.current = false;
      loadDashboard(false);
      triggerAutoSyncIfEligible();
    };

    window.addEventListener('auth-session-changed', handleRefresh);
    window.addEventListener('refresh-dashboard-data', handleRefresh);
    window.addEventListener('storage', handleRefresh);

    return () => {
      window.removeEventListener('auth-session-changed', handleRefresh);
      window.removeEventListener('refresh-dashboard-data', handleRefresh);
      window.removeEventListener('storage', handleRefresh);
    };
  }, []);

  const handleToggleTask = async (id: number, currentStatus: boolean) => {
    try {
      await api.updateActionItem(id, { completed: !currentStatus });
      loadDashboard();
    } catch (err) {
      console.error('Failed to toggle task:', err);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-4 xl:grid-cols-8 gap-3">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="h-24 bg-white rounded-xl border border-slate-200 animate-pulse" />
          ))}
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-72 bg-white rounded-xl border border-slate-200 animate-pulse" />
          <div className="h-72 bg-white rounded-xl border border-slate-200 animate-pulse" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-slate-200 shadow-sm">
        <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-800">Unable to load dashboard intelligence</h3>
        <p className="text-xs text-slate-500 mt-1 mb-4">{error}</p>
        <button
          onClick={() => loadDashboard(true)}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-medium hover:bg-indigo-700 transition-all"
        >
          Try Again
        </button>
      </div>
    );
  }

  const { metrics, priority_emails, upcoming_deadlines, expired_deadlines = [], upcoming_meetings, pending_tasks, recent_emails = [] } = data;

  const kpis = [
    {
      title: 'Total Emails',
      value: metrics.total_emails,
      icon: Mail,
      color: 'text-slate-700',
      bg: 'bg-slate-100',
      link: '/inbox'
    },
    {
      title: 'Unread',
      value: metrics.unread_emails,
      icon: Inbox,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      link: '/inbox?is_read=false'
    },
    {
      title: 'High Priority',
      value: metrics.high_priority_count,
      icon: AlertTriangle,
      color: 'text-rose-600',
      bg: 'bg-rose-50',
      link: '/priority?level=HIGH'
    },
    {
      title: 'Medium Priority',
      value: metrics.medium_priority_count ?? 0,
      icon: AlertTriangle,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      link: '/priority?level=MEDIUM'
    },
    {
      title: 'Low Priority',
      value: metrics.low_priority_count ?? 0,
      icon: CheckCircle2,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
      link: '/priority?level=LOW'
    },
    {
      title: 'Deadlines',
      value: metrics.upcoming_deadlines_count,
      icon: Clock,
      color: 'text-orange-600',
      bg: 'bg-orange-50',
      link: '/deadlines'
    },
    {
      title: 'Meetings',
      value: metrics.upcoming_meetings_count,
      icon: Calendar,
      color: 'text-indigo-600',
      bg: 'bg-indigo-50',
      link: '/meetings'
    },
    {
      title: 'Pending Tasks',
      value: metrics.pending_actions_count,
      icon: CheckSquare,
      color: 'text-teal-600',
      bg: 'bg-teal-50',
      link: '/action-items?completed=false'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Operating Environment & Provenance Status Banner */}
      <div className="p-4 bg-gradient-to-r from-slate-900 via-indigo-950 to-slate-900 text-white rounded-xl shadow-sm border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-indigo-500/20 border border-indigo-400/30 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-4 h-4 text-indigo-300" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="text-xs font-bold text-white tracking-wide">
                {currentUser?.provider_type === 'gmail' ? 'Live Gmail Ingestion Active' : 'Hackathon Demonstration Environment'}
              </span>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${
                currentUser?.provider_type === 'gmail'
                  ? 'bg-emerald-950 text-emerald-300 border-emerald-700/50'
                  : 'bg-indigo-900/80 text-indigo-200 border-indigo-600/40'
              }`}>
                {currentUser?.provider_type === 'gmail' ? 'Live Ingestion' : 'Deterministic Mock AI'}
              </span>
            </div>
            <p className="text-[11px] text-slate-300 mt-0.5">
              {currentUser?.provider_type === 'gmail'
                ? `Ingesting live authenticated correspondence for ${currentUser?.email || 'User'}`
                : `15 pre-loaded university circulars with deterministic semantic extraction for ${currentUser?.name || 'Dr. Faculty'}`}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2 self-start sm:self-auto">
          {syncStatus && (
            <div
              className={`flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium rounded-full transition-all duration-300 shadow-sm ${
                syncStatus.includes('Syncing')
                  ? 'bg-indigo-900 text-indigo-200 border border-indigo-700'
                  : 'bg-emerald-900 text-emerald-200 border border-emerald-700'
              }`}
            >
              {syncStatus.includes('Syncing') ? (
                <RefreshCw className="w-3 h-3 text-indigo-300 animate-spin" />
              ) : (
                <CheckCircle2 className="w-3 h-3 text-emerald-300" />
              )}
              <span>{syncStatus}</span>
            </div>
          )}
          <button
            onClick={() => navigate('/inbox')}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-200 bg-slate-800/80 hover:bg-slate-800 border border-slate-700 rounded-lg shadow-sm transition-all"
          >
            <Inbox className="w-3.5 h-3.5 text-slate-400" />
            <span>Open Inbox</span>
          </button>
        </div>
      </div>

      {/* KPI Metric Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        {kpis.map((kpi, i) => {
          const Icon = kpi.icon;
          return (
            <div
              key={i}
              onClick={() => navigate(kpi.link)}
              className="p-4 bg-white rounded-xl border border-slate-200 hover:border-indigo-300 hover:shadow-sm cursor-pointer transition-all flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-medium text-slate-500">{kpi.title}</span>
                <div className={`p-1.5 rounded-lg ${kpi.bg}`}>
                  <Icon className={`w-3.5 h-3.5 ${kpi.color}`} />
                </div>
              </div>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-2xl font-bold text-slate-900">{kpi.value}</span>
                {kpi.title === 'High Priority' && (
                  <span className="text-[10px] text-slate-400 font-medium">
                    Med: {metrics.medium_priority_count ?? 0}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Two Column Grid: Priority Emails & Upcoming Deadlines */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* High Priority Emails Feed */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <h3 className="text-sm font-semibold text-slate-900">Urgent &amp; High Priority Emails</h3>
            </div>
            <button
              onClick={() => navigate('/priority')}
              className="text-xs font-medium text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="divide-y divide-slate-100 flex-1 overflow-y-auto max-h-80">
            {priority_emails.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">No high priority emails pending.</div>
            ) : (
              priority_emails.map((email) => {
                const priorityBadge = getPriorityBadge(email.priority);
                const categoryBadge = getCategoryBadge(email.category);
                const senderInitials = email.sender.slice(0, 2).toUpperCase();
                return (
                  <div
                    key={email.id}
                    onClick={() => navigate(`/emails/${email.id}`)}
                    className="p-4 hover:bg-slate-50/80 cursor-pointer transition-all flex items-start space-x-3"
                  >
                    <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 text-slate-700 font-bold text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                      {senderInitials}
                    </div>

                    <div className="flex-1 min-w-0 space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-semibold text-slate-800 truncate max-w-[220px]">
                          {email.sender}
                        </span>
                        <span className="text-[11px] text-slate-400">{formatRelativeTime(email.received_at)}</span>
                      </div>

                      <h4 className="text-xs font-medium text-slate-900 line-clamp-1">{email.subject}</h4>

                      {email.priority_reason && (
                        <p className="text-[11px] text-slate-500 line-clamp-1 italic bg-rose-50/60 px-2 py-0.5 rounded border border-rose-100">
                          {email.priority_reason}
                        </p>
                      )}

                      <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                        {email.priority && (
                          <span
                            className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${priorityBadge.bg} ${priorityBadge.text} ${priorityBadge.border}`}
                          >
                            {priorityBadge.label}
                          </span>
                        )}
                        {email.category && (
                          <span className={`text-[10px] font-medium px-2 py-0.5 rounded ${categoryBadge.bg} ${categoryBadge.text}`}>
                            {email.category}
                          </span>
                        )}
                        {email.action_items_count > 0 && (
                          <span className="text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                            {email.action_items_count} Action{email.action_items_count > 1 ? 's' : ''}
                          </span>
                        )}
                        {email.has_deadline && (
                          <span className="text-[10px] text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200 flex items-center">
                            <Clock className="w-2.5 h-2.5 mr-1" />
                            Deadline
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Upcoming Deadlines Widget with Direct Task Checkbox */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Clock className="w-4 h-4 text-amber-600" />
              <h3 className="text-sm font-semibold text-slate-900">Upcoming Academic Deadlines</h3>
            </div>
            <button
              onClick={() => navigate('/deadlines')}
              className="text-xs font-medium text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="divide-y divide-slate-100 flex-1 overflow-y-auto max-h-80">
            {upcoming_deadlines.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400 space-y-1">
                <Clock className="w-6 h-6 text-slate-300 mx-auto mb-1.5" />
                <p className="font-medium text-slate-600">No approaching deadlines pending</p>
                <p className="text-[11px] text-slate-400">All current calendar obligations are completed or logged.</p>
              </div>
            ) : (
              upcoming_deadlines.map((item) => {
                const relBadge = getRelationshipBadge(item.relationship_type);
                const statusBadge = getDeadlineStatusBadge(item.deadline_status);
                return (
                  <div
                    key={item.id}
                    className="p-4 hover:bg-slate-50/80 transition-all flex items-start space-x-3"
                  >
                    <button
                      onClick={() => handleToggleTask(item.id, item.completed)}
                      className="mt-0.5 text-slate-400 hover:text-emerald-600 transition-all flex-shrink-0"
                      title={item.completed ? 'Mark pending' : 'Mark completed'}
                    >
                      {item.completed ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                      ) : (
                        <Circle className="w-4 h-4 text-slate-300 hover:text-emerald-500" />
                      )}
                    </button>

                    <div className="flex-1 space-y-1">
                      <div className="flex flex-wrap items-center gap-1.5">
                        <span className="text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                          {formatDate(item.due_date)}
                        </span>
                        {item.relative_status && (
                          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${statusBadge.bg} ${statusBadge.text} ${statusBadge.border}`}>
                            {item.relative_status}
                          </span>
                        )}
                        <span className={`text-[10px] font-medium px-2 py-0.5 rounded ${relBadge.bg} ${relBadge.text}`}>
                          {relBadge.label}
                        </span>
                      </div>
                      <p className={`text-xs ${item.completed ? 'line-through text-slate-400' : 'text-slate-800 font-medium'}`}>
                        {item.task_description}
                      </p>
                      <button
                        onClick={() => navigate(`/emails/${item.email_id}`)}
                        className="text-[11px] text-slate-400 hover:text-indigo-600 flex items-center space-x-1 transition-all"
                      >
                        <span className="truncate max-w-[280px]">From: {item.email_subject}</span>
                        <ExternalLink className="w-2.5 h-2.5 ml-0.5" />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>

      {/* Expired / Overdue Academic Deadlines Section */}
      {expired_deadlines.length > 0 && (
        <div className="bg-white rounded-xl border border-rose-200 shadow-sm overflow-hidden">
          <div className="px-5 py-3.5 bg-rose-50/70 border-b border-rose-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              <h3 className="text-sm font-semibold text-rose-900">Expired / Overdue Academic Deadlines</h3>
              <span className="px-2 py-0.5 text-[10px] font-bold bg-rose-200 text-rose-800 rounded-full">
                {expired_deadlines.length} Overdue
              </span>
            </div>
            <button
              onClick={() => navigate('/deadlines')}
              className="text-xs font-medium text-rose-600 hover:text-rose-800 flex items-center space-x-1"
            >
              <span>View All Deadlines</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="divide-y divide-rose-50 overflow-y-auto max-h-60">
            {expired_deadlines.map((item) => (
              <div
                key={item.id}
                className="p-4 hover:bg-rose-50/30 transition-all flex items-start space-x-3"
              >
                <button
                  onClick={() => handleToggleTask(item.id, item.completed)}
                  className="mt-0.5 text-slate-400 hover:text-emerald-600 transition-all flex-shrink-0"
                  title={item.completed ? 'Mark pending' : 'Mark completed'}
                >
                  {item.completed ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  ) : (
                    <Circle className="w-4 h-4 text-rose-300 hover:text-emerald-500" />
                  )}
                </button>

                <div className="flex-1 space-y-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-semibold text-rose-700 bg-rose-100/80 px-2 py-0.5 rounded border border-rose-200">
                      {formatDate(item.due_date)}
                    </span>
                    <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-600 text-white uppercase tracking-wider">
                      OVERDUE
                    </span>
                    {item.relative_status && (
                      <span className="text-[11px] font-medium text-rose-600">
                        {item.relative_status}
                      </span>
                    )}
                  </div>
                  <p className={`text-xs ${item.completed ? 'line-through text-slate-400' : 'text-slate-800 font-medium'}`}>
                    {item.task_description}
                  </p>
                  <button
                    onClick={() => navigate(`/emails/${item.email_id}`)}
                    className="text-[11px] text-slate-400 hover:text-indigo-600 flex items-center space-x-1 transition-all"
                  >
                    <span className="truncate max-w-[280px]">From: {item.email_subject}</span>
                    <ExternalLink className="w-2.5 h-2.5 ml-0.5" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Two Column Grid: Upcoming Meetings & Quick Action Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Scheduled Meetings Widget */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Calendar className="w-4 h-4 text-indigo-600" />
              <h3 className="text-sm font-semibold text-slate-900">Scheduled Academic Meetings</h3>
            </div>
            <button
              onClick={() => navigate('/meetings')}
              className="text-xs font-medium text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
            >
              <span>View All</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="divide-y divide-slate-100 flex-1 overflow-y-auto max-h-80">
            {upcoming_meetings.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400">No meetings currently scheduled.</div>
            ) : (
              upcoming_meetings.map((m) => (
                <div key={m.id} className="p-4 hover:bg-slate-50/80 transition-all space-y-1.5">
                  <div className="flex items-center justify-between">
                    <h4 className="text-xs font-semibold text-slate-900">{m.title}</h4>
                    <span className="text-[11px] font-medium text-indigo-700 bg-indigo-50 px-2 py-0.5 rounded border border-indigo-100">
                      {formatDate(m.meeting_date)} {m.meeting_time ? `@ ${m.meeting_time}` : ''}
                    </span>
                  </div>

                  {m.location && (
                    <div className="flex items-center text-xs text-slate-600">
                      <MapPin className="w-3.5 h-3.5 mr-1 text-slate-400 flex-shrink-0" />
                      <span>{m.location}</span>
                    </div>
                  )}

                  {m.preparation && (
                    <div className="text-[11px] text-amber-800 bg-amber-50/70 px-2.5 py-1 rounded border border-amber-200/60">
                      <span className="font-medium">Preparation:</span> {m.preparation}
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* Pending Action Items Quick Checklist */}
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <CheckSquare className="w-4 h-4 text-emerald-600" />
              <h3 className="text-sm font-semibold text-slate-900">Pending Action Items</h3>
            </div>
            <button
              onClick={() => navigate('/action-items')}
              className="text-xs font-medium text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
            >
              <span>Manage Tasks</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>

          <div className="divide-y divide-slate-100 flex-1 overflow-y-auto max-h-80">
            {pending_tasks.length === 0 ? (
              <div className="p-8 text-center text-xs text-slate-400 space-y-1">
                <CheckCircle2 className="w-6 h-6 text-emerald-500 mx-auto mb-1.5" />
                <p className="font-semibold text-slate-700">All actionable duties completed!</p>
                <p className="text-[11px] text-slate-400">Zero pending obligations across active circulars.</p>
              </div>
            ) : (
              pending_tasks.map((task) => (
                <div
                  key={task.id}
                  className="p-3.5 hover:bg-slate-50/80 transition-all flex items-start space-x-3"
                >
                  <button
                    onClick={() => handleToggleTask(task.id, task.completed)}
                    className="mt-0.5 text-slate-400 hover:text-emerald-600 transition-all flex-shrink-0"
                  >
                    {task.completed ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    ) : (
                      <Circle className="w-4 h-4 text-slate-300 hover:text-emerald-500" />
                    )}
                  </button>

                  <div className="flex-1 space-y-0.5">
                    <p className={`text-xs ${task.completed ? 'line-through text-slate-400' : 'text-slate-800 font-medium'}`}>
                      {task.description}
                    </p>
                    <div className="flex items-center space-x-2 text-[11px] text-slate-400">
                      {task.due_date && <span>Due: {formatDate(task.due_date)}</span>}
                      {task.email_subject && (
                        <button
                          onClick={() => navigate(`/emails/${task.email_id}`)}
                          className="hover:text-indigo-600 truncate max-w-[200px]"
                        >
                          • {task.email_subject}
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Recent Incoming Correspondence Feed */}
      {recent_emails && recent_emails.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Mail className="w-4 h-4 text-indigo-600" />
              <h3 className="text-sm font-semibold text-slate-900">Recent Incoming Correspondence</h3>
            </div>
            <button
              onClick={() => navigate('/inbox')}
              className="text-xs font-medium text-indigo-600 hover:text-indigo-800 flex items-center space-x-1"
            >
              <span>View All in Inbox</span>
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
          <div className="divide-y divide-slate-100">
            {recent_emails.map((email) => {
              const priorityBadge = getPriorityBadge(email.priority);
              const categoryBadge = getCategoryBadge(email.category);
              return (
                <div
                  key={email.id}
                  onClick={() => navigate(`/emails/${email.id}`)}
                  className="p-4 hover:bg-slate-50/80 cursor-pointer transition-all flex items-center justify-between space-x-4"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-xs font-semibold text-slate-800 truncate max-w-[220px]">
                        {email.sender}
                      </span>
                      <span className="text-[11px] text-slate-400">
                        {formatRelativeTime(email.received_at)}
                      </span>
                      {!email.is_read && (
                        <span className="inline-block w-2 h-2 rounded-full bg-blue-600" title="Unread" />
                      )}
                    </div>
                    <h4 className="text-xs font-medium text-slate-900 truncate">{email.subject}</h4>
                    <p className="text-[11px] text-slate-500 truncate mt-0.5">{email.body_preview}</p>
                  </div>
                  <div className="flex items-center space-x-2 flex-shrink-0">
                    {email.priority && (
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${priorityBadge.bg} ${priorityBadge.text} ${priorityBadge.border}`}>
                        {priorityBadge.label}
                      </span>
                    )}
                    {email.category && (
                      <span className={`text-[10px] font-medium px-2 py-0.5 rounded ${categoryBadge.bg} ${categoryBadge.text}`}>
                        {email.category}
                      </span>
                    )}
                    {email.has_analysis && (
                      <span className="text-[10px] text-indigo-600 hidden sm:flex items-center">
                        <Sparkles className="w-3 h-3 mr-1" />
                        AI Synthesized
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
