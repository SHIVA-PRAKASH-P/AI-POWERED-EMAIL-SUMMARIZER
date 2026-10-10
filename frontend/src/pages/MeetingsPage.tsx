import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Calendar, Clock, MapPin, ExternalLink, AlertTriangle } from 'lucide-react';
import { api } from '../services/api';
import { Meeting } from '../types';
import { formatDate } from '../utils/formatters';

export const MeetingsPage: React.FC = () => {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadMeetings = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getMeetings();
      setMeetings(data);
    } catch (err: any) {
      console.error('Failed to load meetings:', err);
      setError(err.message || 'Failed to load scheduled meetings');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMeetings();
  }, []);

  return (
    <div className="space-y-5">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-slate-900 tracking-tight">Scheduled Academic Meetings</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Extracted committee sessions, review audits, and departmental council meetings with venue and prep notes.
        </p>
      </div>

      {/* Meetings Grid / Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {loading ? (
          [...Array(4)].map((_, i) => (
            <div key={i} className="h-44 bg-white rounded-xl border border-slate-200 animate-pulse" />
          ))
        ) : error ? (
          <div className="col-span-2 p-8 text-center bg-white rounded-xl border border-slate-200 shadow-sm">
            <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-800">Error Loading Meetings</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4">{error}</p>
            <button
              onClick={loadMeetings}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-all"
            >
              Try Again
            </button>
          </div>
        ) : meetings.length === 0 ? (
          <div className="col-span-2 p-12 text-center bg-white rounded-xl border border-slate-200">
            <Calendar className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h4 className="text-sm font-semibold text-slate-700">No upcoming meetings detected</h4>
            <p className="text-xs text-slate-400 mt-1">
              Meetings extracted by the AI Orchestrator will be indexed here automatically.
            </p>
          </div>
        ) : (
          meetings.map((m) => (
            <div
              key={m.id}
              className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm hover:border-indigo-300 hover:shadow-md transition-all flex flex-col justify-between space-y-3"
            >
              <div className="space-y-2">
                <div className="flex items-start justify-between gap-2">
                  <h3 className="text-xs font-bold text-slate-900 leading-snug">{m.title}</h3>
                  <span className="text-xs font-semibold text-indigo-700 bg-indigo-50 px-2.5 py-0.5 rounded border border-indigo-200 flex-shrink-0">
                    {formatDate(m.meeting_date)}
                  </span>
                </div>

                <div className="flex flex-wrap items-center gap-3 text-xs text-slate-600">
                  {m.meeting_time && (
                    <div className="flex items-center">
                      <Clock className="w-3.5 h-3.5 mr-1 text-slate-400" />
                      <span>{m.meeting_time} hrs</span>
                    </div>
                  )}
                  {m.location && (
                    <div className="flex items-center">
                      <MapPin className="w-3.5 h-3.5 mr-1 text-indigo-500" />
                      <span className="font-medium text-slate-800">{m.location}</span>
                    </div>
                  )}
                </div>

                {m.preparation && (
                  <div className="p-2.5 bg-amber-50/80 rounded-lg border border-amber-200/70 text-[11px] text-amber-900">
                    <span className="font-semibold block mb-0.5">Prerequisite Checklist:</span>
                    <p className="leading-normal">{m.preparation}</p>
                  </div>
                )}
              </div>

              {/* Source Email link */}
              <div className="pt-2 border-t border-slate-100 flex items-center justify-between">
                <button
                  onClick={() => navigate(`/emails/${m.email_id}`)}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-medium flex items-center space-x-1"
                >
                  <span className="truncate max-w-[260px]">From: {m.email_subject}</span>
                  <ExternalLink className="w-3 h-3 ml-0.5 flex-shrink-0" />
                </button>
                <span className="text-[10px] text-slate-400 font-mono">ID #{m.email_id}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
