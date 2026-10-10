import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { CheckCircle2, Circle, ExternalLink, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { DeadlineItem } from '../types';
import {
  formatDate,
  getPriorityBadge,
  getRelationshipBadge
} from '../utils/formatters';

export const DeadlinesPage: React.FC = () => {
  const [deadlines, setDeadlines] = useState<DeadlineItem[]>([]);
  const [statusFilter, setStatusFilter] = useState<'all' | 'pending' | 'completed'>('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadDeadlines = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDeadlines(statusFilter);
      setDeadlines(data);
    } catch (err: any) {
      console.error('Failed to load deadlines:', err);
      setError(err.message || 'Failed to load academic deadlines');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDeadlines();
  }, [statusFilter]);

  const handleToggleCompleted = async (id: number, currentCompleted: boolean) => {
    try {
      await api.updateActionItem(id, { completed: !currentCompleted });
      loadDeadlines();
    } catch (err) {
      console.error('Failed to toggle status:', err);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Academic Deadlines Calendar</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Chronological academic timelines normalized from correspondence and tied to actionable obligations.
          </p>
        </div>

        {/* Status Filters */}
        <div className="inline-flex p-1 bg-slate-200/70 rounded-lg text-xs font-semibold">
          {(['all', 'pending', 'completed'] as const).map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-3 py-1.5 rounded-md capitalize transition-all ${
                statusFilter === st
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Deadlines Timeline List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-100">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading academic deadlines...</div>
        ) : error ? (
          <div className="p-8 text-center bg-white rounded-xl">
            <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-800">Error Loading Deadlines</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4">{error}</p>
            <button
              onClick={loadDeadlines}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-all"
            >
              Try Again
            </button>
          </div>
        ) : deadlines.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">
            No deadlines recorded under the "{statusFilter}" filter.
          </div>
        ) : (
          deadlines.map((item) => {
            const priorityBadge = getPriorityBadge(item.priority);
            const relBadge = getRelationshipBadge(item.relationship_type);

            return (
              <div
                key={item.id}
                className={`p-4 sm:p-5 flex items-start space-x-4 transition-all ${
                  item.completed ? 'bg-slate-50/70' : 'hover:bg-slate-50/80'
                }`}
              >
                {/* Toggle Status Checkbox */}
                <button
                  onClick={() => handleToggleCompleted(item.id, item.completed)}
                  className="mt-1 text-slate-400 hover:text-emerald-600 transition-all flex-shrink-0"
                >
                  {item.completed ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  ) : (
                    <Circle className="w-5 h-5 text-slate-300 hover:text-emerald-500" />
                  )}
                </button>

                {/* Deadline Content */}
                <div className="flex-1 space-y-1.5 min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-bold text-rose-700 bg-rose-50 px-2.5 py-0.5 rounded border border-rose-200">
                      {formatDate(item.due_date)}
                    </span>
                    <span className={`text-[10px] font-semibold px-2 py-0.5 rounded ${relBadge.bg} ${relBadge.text}`}>
                      {relBadge.label}
                    </span>
                    <span
                      className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${priorityBadge.bg} ${priorityBadge.text} ${priorityBadge.border}`}
                    >
                      {priorityBadge.label}
                    </span>
                    {item.completed && (
                      <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        COMPLETED
                      </span>
                    )}
                  </div>

                  <h3 className={`text-xs ${item.completed ? 'line-through text-slate-400' : 'text-slate-900 font-semibold'}`}>
                    {item.task_description}
                  </h3>

                  {item.relationship_reason && (
                    <p className="text-[11px] text-slate-500 italic">
                      {item.relationship_reason}
                    </p>
                  )}

                  <div className="flex items-center space-x-2 pt-1">
                    <button
                      onClick={() => navigate(`/emails/${item.email_id}`)}
                      className="text-[11px] text-indigo-600 hover:text-indigo-800 font-medium flex items-center space-x-1"
                    >
                      <span className="truncate max-w-[320px]">From: {item.email_subject}</span>
                      <ExternalLink className="w-3 h-3 ml-0.5" />
                    </button>
                    <span className="text-slate-300">•</span>
                    <span className="text-[11px] text-slate-400">Sender: {item.email_sender}</span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
