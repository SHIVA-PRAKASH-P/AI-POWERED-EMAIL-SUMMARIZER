import React, { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Search,
  Inbox as InboxIcon,
  Sparkles,
  Clock,
  RotateCw,
  X,
  AlertTriangle,
  Filter
} from 'lucide-react';
import { api } from '../services/api';
import { EmailSummary, AcademicCategory } from '../types';
import {
  formatRelativeTime,
  getPriorityBadge,
  getCategoryBadge
} from '../utils/formatters';

const CATEGORIES: AcademicCategory[] = [
  'Academic',
  'Administrative',
  'Examination',
  'Meeting',
  'Student',
  'Department',
  'Event',
  'Research',
  'Placement',
  'General'
];

export const InboxPage: React.FC = () => {
  const [emails, setEmails] = useState<EmailSummary[]>([]);
  const [availableCategories, setAvailableCategories] = useState<{ category: string; count: number }[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  // Filter states from URL or defaults
  const search = searchParams.get('search') || '';
  const category = searchParams.get('category') || 'ALL';
  const priority = searchParams.get('priority') || 'ALL';
  const isReadParam = searchParams.get('is_read');
  const hasDeadlineParam = searchParams.get('has_deadline');

  const [searchInput, setSearchInput] = useState(search);

  const loadEmails = async () => {
    try {
      setLoading(true);
      setError(null);
      const params: any = {};
      if (search) params.search = search;
      if (category !== 'ALL') params.category = category;
      if (priority !== 'ALL') params.priority = priority;
      if (isReadParam !== null && isReadParam !== undefined) {
        params.is_read = isReadParam === 'true';
      }
      if (hasDeadlineParam !== null && hasDeadlineParam !== undefined) {
        params.has_deadline = hasDeadlineParam === 'true';
      }

      const list = await api.getEmails(params);
      setEmails(list);
    } catch (err: any) {
      setError(err.message || 'Failed to load inbox correspondence');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    api.getCategories()
      .then((cats) => {
        if (cats && cats.length > 0) {
          setAvailableCategories(cats);
        }
      })
      .catch((err) => console.error('Failed to load categories:', err));
  }, []);

  useEffect(() => {
    setSearchInput(search);
    loadEmails();
  }, [search, category, priority, isReadParam, hasDeadlineParam]);

  const updateFilter = (key: string, value: string | null) => {
    const nextParams = new URLSearchParams(searchParams);
    if (value === null || value === 'ALL') {
      nextParams.delete(key);
    } else {
      nextParams.set(key, value);
    }
    setSearchParams(nextParams);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateFilter('search', searchInput.trim() || null);
  };

  const clearAllFilters = () => {
    setSearchInput('');
    setSearchParams(new URLSearchParams());
  };

  const hasActiveFilters =
    Boolean(search) ||
    category !== 'ALL' ||
    priority !== 'ALL' ||
    isReadParam !== null ||
    hasDeadlineParam !== null;

  return (
    <div className="space-y-5">
      {/* Top Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">Smart Academic Inbox</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Normalized email records with multi-agent priority classification and structured metadata.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={loadEmails}
            className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-lg hover:bg-slate-50 transition-all"
          >
            <RotateCw className="w-3.5 h-3.5 text-slate-400" />
            <span>Reload</span>
          </button>
        </div>
      </div>

      {/* Filter & Search Toolbar */}
      <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-sm space-y-3">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Search Input */}
          <form onSubmit={handleSearchSubmit} className="relative flex-1 max-w-md">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="Search sender, subject, keywords..."
              className="w-full pl-9 pr-8 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500"
            />
            {searchInput && (
              <button
                type="button"
                onClick={() => {
                  setSearchInput('');
                  updateFilter('search', null);
                }}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </form>

          {/* Quick Clear Filter */}
          {hasActiveFilters && (
            <button
              onClick={clearAllFilters}
              className="text-xs text-rose-600 hover:text-rose-800 font-medium flex items-center space-x-1 self-start md:self-auto"
            >
              <X className="w-3.5 h-3.5" />
              <span>Clear Filters</span>
            </button>
          )}
        </div>

        {/* Category Filter Pills (Horizontal Scrollable) */}
        <div className="pt-2 border-t border-slate-100 space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider flex items-center">
              <Filter className="w-3 h-3 mr-1 text-slate-400" />
              Academic Category
            </span>
            <span className="text-[10px] text-slate-400">Click to filter by domain</span>
          </div>

          <div className="flex flex-wrap gap-1.5 overflow-x-auto pb-1 text-xs">
            <button
              onClick={() => updateFilter('category', 'ALL')}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-semibold transition-all ${
                category === 'ALL'
                  ? 'bg-slate-900 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              All Categories
            </button>
            {(availableCategories.length > 0
              ? availableCategories
              : CATEGORIES.map((c) => ({ category: c, count: 0 }))
            ).map((catItem) => {
              const isSelected = category === catItem.category;
              return (
                <button
                  key={catItem.category}
                  onClick={() => updateFilter('category', isSelected ? 'ALL' : catItem.category)}
                  className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all flex items-center space-x-1.5 ${
                    isSelected
                      ? 'bg-indigo-600 text-white font-semibold shadow-xs'
                      : 'bg-slate-50 hover:bg-slate-100 text-slate-700 border border-slate-200/80'
                  }`}
                >
                  <span>{catItem.category}</span>
                  {catItem.count > 0 && (
                    <span
                      className={`text-[10px] px-1 rounded-full font-mono ${
                        isSelected ? 'bg-indigo-800 text-indigo-100' : 'bg-slate-200 text-slate-600'
                      }`}
                    >
                      {catItem.count}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Priority & Status Filter Row */}
        <div className="flex flex-wrap items-center justify-between gap-3 pt-2 border-t border-slate-100 text-xs">
          {/* Priority Color-Coded Chips */}
          <div className="flex items-center space-x-1.5">
            <span className="text-[11px] font-medium text-slate-500 mr-1">Priority:</span>
            <button
              onClick={() => updateFilter('priority', 'ALL')}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                priority === 'ALL'
                  ? 'bg-slate-900 text-white font-semibold'
                  : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
              }`}
            >
              All
            </button>
            <button
              onClick={() => updateFilter('priority', priority === 'HIGH' ? 'ALL' : 'HIGH')}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                priority === 'HIGH'
                  ? 'bg-rose-600 text-white font-bold shadow-xs'
                  : 'bg-rose-50 text-rose-700 border border-rose-200 hover:bg-rose-100'
              }`}
            >
              High
            </button>
            <button
              onClick={() => updateFilter('priority', priority === 'MEDIUM' ? 'ALL' : 'MEDIUM')}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                priority === 'MEDIUM'
                  ? 'bg-amber-600 text-white font-bold shadow-xs'
                  : 'bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100'
              }`}
            >
              Medium
            </button>
            <button
              onClick={() => updateFilter('priority', priority === 'LOW' ? 'ALL' : 'LOW')}
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                priority === 'LOW'
                  ? 'bg-emerald-600 text-white font-bold shadow-xs'
                  : 'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100'
              }`}
            >
              Low
            </button>
          </div>

          {/* Quick Toggles: Unread & Has Deadline */}
          <div className="flex items-center space-x-2">
            <button
              onClick={() =>
                updateFilter('is_read', isReadParam === 'false' ? null : 'false')
              }
              className={`px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                isReadParam === 'false'
                  ? 'bg-blue-600 text-white font-semibold shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              Unread Only
            </button>

            <button
              onClick={() =>
                updateFilter('has_deadline', hasDeadlineParam === 'true' ? null : 'true')
              }
              className={`flex items-center space-x-1 px-2.5 py-1 rounded-lg text-[11px] font-medium transition-all ${
                hasDeadlineParam === 'true'
                  ? 'bg-amber-600 text-white font-semibold shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              <Clock className="w-3 h-3" />
              <span>Has Deadline</span>
            </button>
          </div>
        </div>

        {/* Active Filter Chips Bar */}
        {hasActiveFilters && (
          <div className="flex flex-wrap items-center gap-1.5 pt-2 border-t border-slate-100 text-xs">
            <span className="text-[11px] font-medium text-slate-400 mr-1">Active filters:</span>
            {search && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] bg-slate-100 text-slate-800 border border-slate-200">
                Search: "{search}"
                <button onClick={() => updateFilter('search', null)} className="ml-1 text-slate-400 hover:text-slate-600">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {category !== 'ALL' && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] bg-indigo-50 text-indigo-700 border border-indigo-200">
                Category: {category}
                <button onClick={() => updateFilter('category', 'ALL')} className="ml-1 text-indigo-400 hover:text-indigo-600">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {priority !== 'ALL' && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] bg-rose-50 text-rose-700 border border-rose-200">
                Priority: {priority}
                <button onClick={() => updateFilter('priority', 'ALL')} className="ml-1 text-rose-400 hover:text-rose-600">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {isReadParam === 'false' && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] bg-blue-50 text-blue-700 border border-blue-200">
                Unread Only
                <button onClick={() => updateFilter('is_read', null)} className="ml-1 text-blue-400 hover:text-blue-600">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            {hasDeadlineParam === 'true' && (
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] bg-amber-50 text-amber-700 border border-amber-200">
                Has Deadline
                <button onClick={() => updateFilter('has_deadline', null)} className="ml-1 text-amber-400 hover:text-amber-600">
                  <X className="w-3 h-3" />
                </button>
              </span>
            )}
            <button
              onClick={clearAllFilters}
              className="text-[11px] text-rose-600 hover:text-rose-800 font-semibold ml-1.5 underline"
            >
              Reset all
            </button>
          </div>
        )}
      </div>

      {/* Email List Table/Feed */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
        {loading ? (
          <div className="divide-y divide-slate-100">
            {[...Array(6)].map((_, i) => (
              <div key={i} className="p-4 flex items-center justify-between animate-pulse">
                <div className="space-y-2 flex-1">
                  <div className="h-3.5 bg-slate-200 rounded w-1/4" />
                  <div className="h-3 bg-slate-100 rounded w-3/4" />
                </div>
                <div className="h-3 bg-slate-100 rounded w-16" />
              </div>
            ))}
          </div>
        ) : error ? (
          <div className="p-8 text-center bg-white rounded-xl">
            <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-2" />
            <h3 className="text-sm font-semibold text-slate-800">Error Loading Correspondence</h3>
            <p className="text-xs text-slate-500 mt-1 mb-4">{error}</p>
            <button
              onClick={loadEmails}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-all"
            >
              Try Again
            </button>
          </div>
        ) : emails.length === 0 ? (
          <div className="p-12 text-center">
            <InboxIcon className="w-10 h-10 text-slate-300 mx-auto mb-2" />
            <h4 className="text-sm font-semibold text-slate-700">No emails matched your criteria</h4>
            <p className="text-xs text-slate-400 mt-1">Try resetting your search query or filters.</p>
            {hasActiveFilters && (
              <button
                onClick={clearAllFilters}
                className="mt-3 px-3 py-1.5 text-xs bg-slate-100 hover:bg-slate-200 rounded-lg text-slate-700 font-medium transition-all"
              >
                Clear all filters
              </button>
            )}
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {emails.map((email) => {
              const priorityBadge = getPriorityBadge(email.priority);
              const categoryBadge = getCategoryBadge(email.category);

              return (
                <div
                  key={email.id}
                  onClick={() => navigate(`/emails/${email.id}`)}
                  className={`p-4 hover:bg-slate-50/90 cursor-pointer transition-all flex items-start space-x-3.5 ${
                    !email.is_read ? 'bg-blue-50/25' : ''
                  }`}
                >
                  {/* Unread indicator dot */}
                  <div className="pt-2.5 flex-shrink-0">
                    <span
                      className={`block w-2.5 h-2.5 rounded-full ${
                        !email.is_read ? 'bg-blue-600 shadow-sm shadow-blue-500/50' : 'bg-slate-300'
                      }`}
                    />
                  </div>

                  {/* Sender Avatar */}
                  <div className="w-8 h-8 rounded-full bg-slate-100 border border-slate-200 text-slate-700 font-bold text-xs flex items-center justify-center flex-shrink-0 mt-0.5">
                    {email.sender.slice(0, 2).toUpperCase()}
                  </div>

                  {/* Main Content */}
                  <div className="flex-1 min-w-0 space-y-1">
                    {/* Header: Sender & Received time */}
                    <div className="flex items-center justify-between">
                      <span className={`text-xs truncate ${!email.is_read ? 'font-bold text-slate-900' : 'font-medium text-slate-700'}`}>
                        {email.sender}
                      </span>
                      <span className="text-[11px] text-slate-400 flex-shrink-0 ml-2">
                        {formatRelativeTime(email.received_at)}
                      </span>
                    </div>

                    {/* Subject line */}
                    <h3 className={`text-xs ${!email.is_read ? 'font-semibold text-slate-950' : 'font-medium text-slate-800'}`}>
                      {email.subject}
                    </h3>

                    {/* Preview Snippet */}
                    <p className="text-xs text-slate-500 line-clamp-1">
                      {email.body_preview}
                    </p>

                    {/* Metadata Badges */}
                    <div className="flex flex-wrap items-center gap-2 pt-1">
                      {email.priority && (
                        <span
                          className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${priorityBadge.bg} ${priorityBadge.text} ${priorityBadge.border}`}
                        >
                          {priorityBadge.label}
                        </span>
                      )}

                      {email.category && (
                        <span
                          className={`text-[10px] font-medium px-2 py-0.5 rounded ${categoryBadge.bg} ${categoryBadge.text}`}
                        >
                          {email.category}
                        </span>
                      )}

                      {email.has_deadline && (
                        <span className="inline-flex items-center text-[10px] font-medium text-amber-700 bg-amber-50 px-1.5 py-0.5 rounded border border-amber-200">
                          <Clock className="w-2.5 h-2.5 mr-1" />
                          Deadline
                        </span>
                      )}

                      {email.action_items_count > 0 && (
                        <span className="text-[10px] text-emerald-700 bg-emerald-50 px-1.5 py-0.5 rounded border border-emerald-200">
                          {email.action_items_count} Action{email.action_items_count > 1 ? 's' : ''}
                        </span>
                      )}

                      {email.has_analysis && (
                        <span className="inline-flex items-center text-[10px] font-medium text-indigo-700 bg-indigo-50 px-1.5 py-0.5 rounded border border-indigo-200">
                          <Sparkles className="w-2.5 h-2.5 mr-1 text-indigo-600" />
                          AI Intelligence Ready
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
