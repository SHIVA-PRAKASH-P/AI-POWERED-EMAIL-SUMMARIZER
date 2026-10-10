import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, ArrowRight, ShieldAlert, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { EmailSummary, PriorityLevel } from '../types';
import {
  formatRelativeTime,
  getPriorityBadge,
  getCategoryBadge
} from '../utils/formatters';

export const PriorityPage: React.FC = () => {
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [selectedPriority, setSelectedPriority] = useState<PriorityLevel | 'ALL'>('HIGH');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadPriorityEmails = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = {};
      if (selectedPriority !== 'ALL') {
        params.priority = selectedPriority;
      }
      const data = await api.getEmails(params);
      setEmails(data);
    } catch (err: any) {
      console.error('Failed to load priority emails:', err);
      setError(err.message || 'Failed to load priority correspondence');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPriorityEmails();
  }, [selectedPriority]);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Context-Aware Priority Center</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Emails triaged via transparent multi-factor scoring (sender statutory authority, deadlines, consequence indicators).
          </p>
        </div>

        {/* Priority Tabs */}
        <div className="inline-flex p-1 bg-slate-200/70 rounded-lg text-xs font-semibold">
          {(['HIGH', 'MEDIUM', 'LOW', 'ALL'] as const).map((lvl) => (
            <button
              key={lvl}
              onClick={() => setSelectedPriority(lvl)}
              className={`px-3 py-1.5 rounded-md transition-all ${
                selectedPriority === lvl
                  ? 'bg-white text-slate-900 shadow-xs'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              {lvl} {lvl !== 'ALL' ? 'Priority' : ''}
            </button>
          ))}
        </div>
      </div>

      {/* Priority Engine Technical Transparency Banner */}
      <div className="p-4 bg-indigo-50/60 border border-indigo-100 rounded-xl text-xs text-indigo-900 flex items-start space-x-3">
        <ShieldAlert className="w-4 h-4 text-indigo-600 mt-0.5 flex-shrink-0" />
        <div className="space-y-1">
          <p className="font-semibold">Explainable Academic Priority Formulation</p>
          <p className="text-indigo-700/90 leading-relaxed text-[11px]">
            Priority is derived from institutional hierarchy weighting (Registrar/Deans/COE = Statutory Authority),
            temporal proximity to exam/marks deadlines, mandatory modal verbs (*"strictly mandatory"*), and accreditation stakes.
          </p>
        </div>
      </div>

      {/* List of Priority Emails */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden divide-y divide-slate-100">
        {loading ? (
          <div className="p-12 text-center text-xs text-slate-400">Evaluating correspondence priority...</div>
        ) : error ? (
          <div className="p-8 text-center bg-white rounded-xl">
            <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-800">Error Loading Priority Emails</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4">{error}</p>
            <button
              onClick={loadPriorityEmails}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-all"
            >
              Try Again
            </button>
          </div>
        ) : emails.length === 0 ? (
          <div className="p-12 text-center text-xs text-slate-400">
            No emails matching priority level "{selectedPriority}".
          </div>
        ) : (
          emails.map((email) => {
            const badge = getPriorityBadge(email.priority);
            const catBadge = getCategoryBadge(email.category);

            return (
              <div
                key={email.id}
                onClick={() => navigate(`/emails/${email.id}`)}
                className="p-4 sm:p-5 hover:bg-slate-50/90 cursor-pointer transition-all space-y-2"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded border ${badge.bg} ${badge.text} ${badge.border}`}
                    >
                      {badge.label}
                    </span>
                    {email.category && (
                      <span className={`text-[10px] font-medium px-2 py-0.5 rounded ${catBadge.bg} ${catBadge.text}`}>
                        {email.category}
                      </span>
                    )}
                  </div>
                  <span className="text-[11px] text-slate-400">{formatRelativeTime(email.received_at)}</span>
                </div>

                <div>
                  <h3 className="text-xs font-bold text-slate-900 leading-tight">{email.subject}</h3>
                  <p className="text-[11px] text-slate-500 mt-0.5">Sender: {email.sender}</p>
                </div>

                {email.priority_reason && (
                  <div className="p-2.5 bg-slate-50 rounded-lg border border-slate-200/70 text-[11px] text-slate-700 space-y-0.5">
                    <span className="font-semibold text-slate-500 uppercase text-[10px] block">
                      Multi-Factor Justification:
                    </span>
                    <p className="italic">"{email.priority_reason}"</p>
                  </div>
                )}

                <div className="flex items-center justify-between pt-1">
                  <div className="flex items-center space-x-3 text-[11px] text-slate-500">
                    {email.has_deadline && (
                      <span className="flex items-center text-rose-700 font-medium">
                        <Clock className="w-3 h-3 mr-1" />
                        Approaching Deadline
                      </span>
                    )}
                    {email.action_items_count > 0 && (
                      <span>{email.action_items_count} Action Item{email.action_items_count > 1 ? 's' : ''}</span>
                    )}
                  </div>

                  <span className="text-xs font-semibold text-indigo-600 flex items-center space-x-1 hover:underline">
                    <span>Inspect Intelligence</span>
                    <ArrowRight className="w-3 h-3" />
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
