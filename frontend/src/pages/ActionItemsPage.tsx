import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  CheckCircle2,
  Circle,
  ExternalLink,
  Clock,
  AlertTriangle
} from 'lucide-react';
import { api } from '../services/api';
import { ActionItem } from '../types';
import {
  formatDate,
  getPriorityBadge,
  getRelationshipBadge
} from '../utils/formatters';

export const ActionItemsPage: React.FC = () => {
  const [actions, setActions] = useState<ActionItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const completedParam = searchParams.get('completed');
  const priorityParam = searchParams.get('priority') || 'ALL';
  const relParam = searchParams.get('relationship') || 'ALL';

  const loadActionItems = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = {};
      if (completedParam !== null && completedParam !== undefined) {
        params.completed = completedParam === 'true';
      }
      if (priorityParam !== 'ALL') {
        params.priority = priorityParam;
      }
      if (relParam !== 'ALL') {
        params.relationship_type = relParam;
      }
      const data = await api.getActionItems(params);
      setActions(data);
    } catch (err: any) {
      console.error('Failed to load action items:', err);
      setError(err.message || 'Failed to load action items');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActionItems();
  }, [completedParam, priorityParam, relParam]);

  const updateParam = (key: string, val: string | null) => {
    const next = new URLSearchParams(searchParams);
    if (val === null || val === 'ALL') {
      next.delete(key);
    } else {
      next.set(key, val);
    }
    setSearchParams(next);
  };

  const handleToggleCompleted = async (id: number, currentCompleted: boolean) => {
    try {
      await api.updateActionItem(id, { completed: !currentCompleted });
      // Optimistic update
      setActions((prev) =>
        prev.map((a) => (a.id === id ? { ...a, completed: !currentCompleted } : a))
      );
    } catch (err) {
      console.error('Failed to toggle completion:', err);
      loadActionItems();
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Faculty Action Items & Tasks</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Operational obligations extracted from academic circulars with instant persistence to SQLite database.
          </p>
        </div>

        {/* Completion Tabs */}
        <div className="inline-flex p-1 bg-slate-200/70 rounded-lg text-xs font-semibold">
          <button
            onClick={() => updateParam('completed', null)}
            className={`px-3 py-1.5 rounded-md transition-all ${
              completedParam === null ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
            }`}
          >
            All Tasks
          </button>
          <button
            onClick={() => updateParam('completed', 'false')}
            className={`px-3 py-1.5 rounded-md transition-all ${
              completedParam === 'false' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
            }`}
          >
            Pending
          </button>
          <button
            onClick={() => updateParam('completed', 'true')}
            className={`px-3 py-1.5 rounded-md transition-all ${
              completedParam === 'true' ? 'bg-white text-slate-900 shadow-xs' : 'text-slate-600'
            }`}
          >
            Completed
          </button>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white p-3 rounded-xl border border-slate-200 shadow-sm flex flex-wrap items-center gap-3 text-xs">
        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-medium text-slate-500">Priority:</span>
          {(['ALL', 'HIGH', 'MEDIUM', 'LOW'] as const).map((lvl) => (
            <button
              key={lvl}
              onClick={() => updateParam('priority', lvl)}
              className={`px-2 py-0.5 rounded text-[11px] font-medium transition-all ${
                priorityParam === lvl ? 'bg-slate-800 text-white' : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              {lvl}
            </button>
          ))}
        </div>

        <div className="h-4 w-px bg-slate-200" />

        <div className="flex items-center space-x-2">
          <span className="text-[11px] font-medium text-slate-500">Relationship:</span>
          <select
            value={relParam}
            onChange={(e) => updateParam('relationship', e.target.value)}
            className="px-2 py-0.5 text-xs bg-slate-50 border border-slate-200 rounded text-slate-700 font-medium"
          >
            <option value="ALL">All Relationships</option>
            <option value="DUE_ON">Due On (Hard Deadline)</option>
            <option value="PREPARE_BEFORE">Prepare Before (Meeting)</option>
            <option value="ATTEND_BY">Attend By</option>
            <option value="COMMUNICATE_BY">Communicate By</option>
            <option value="STANDALONE">Standalone</option>
          </select>
        </div>
      </div>

      {/* Action Items List */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-100">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400">Loading action items...</div>
        ) : error ? (
          <div className="p-8 text-center bg-white rounded-xl">
            <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-800">Error Loading Action Items</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4">{error}</p>
            <button
              onClick={loadActionItems}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-all"
            >
              Try Again
            </button>
          </div>
        ) : actions.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">
            No action items found matching criteria.
          </div>
        ) : (
          actions.map((item) => {
            const priorityBadge = getPriorityBadge(item.priority);
            const relBadge = getRelationshipBadge(item.relationship_type);

            return (
              <div
                key={item.id}
                className={`p-4 sm:p-5 flex items-start space-x-3.5 transition-all ${
                  item.completed ? 'bg-slate-50/70' : 'hover:bg-slate-50/80'
                }`}
              >
                {/* Instant Checkbox */}
                <button
                  onClick={() => handleToggleCompleted(item.id, item.completed)}
                  className="mt-0.5 text-slate-400 hover:text-emerald-600 transition-all flex-shrink-0"
                >
                  {item.completed ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-600" />
                  ) : (
                    <Circle className="w-5 h-5 text-slate-300 hover:text-emerald-500" />
                  )}
                </button>

                {/* Main Content */}
                <div className="flex-1 min-w-0 space-y-1.5">
                  <div className="flex flex-wrap items-center gap-2">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border ${priorityBadge.bg} ${priorityBadge.text} ${priorityBadge.border}`}
                    >
                      {priorityBadge.label}
                    </span>
                    <span className={`text-[10px] font-medium px-2 py-0.5 rounded ${relBadge.bg} ${relBadge.text}`}>
                      {relBadge.label}
                    </span>
                    {item.due_date && (
                      <span className="text-xs font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200 flex items-center">
                        <Clock className="w-3 h-3 mr-1" />
                        Due: {formatDate(item.due_date)}
                      </span>
                    )}
                    {item.completed && (
                      <span className="text-[10px] font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                        COMPLETED
                      </span>
                    )}
                  </div>

                  <h3 className={`text-xs ${item.completed ? 'line-through text-slate-400' : 'text-slate-900 font-semibold'}`}>
                    {item.description}
                  </h3>

                  {item.relationship_reason && (
                    <p className="text-[11px] text-slate-500 italic">
                      {item.relationship_reason}
                    </p>
                  )}

                  <div className="flex items-center space-x-2 pt-1 text-[11px]">
                    <button
                      onClick={() => navigate(`/emails/${item.email_id}`)}
                      className="text-indigo-600 hover:text-indigo-800 font-medium flex items-center space-x-1"
                    >
                      <span className="truncate max-w-[280px]">From: {item.email_subject}</span>
                      <ExternalLink className="w-3 h-3 ml-0.5" />
                    </button>
                    <span className="text-slate-300">•</span>
                    <span className="text-slate-400">Sender: {item.email_sender}</span>
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
