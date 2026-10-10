import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ArrowLeft,
  Sparkles,
  RotateCw,
  Calendar,
  CheckSquare,
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  Circle,
  MapPin,
  Tag,
  FileText,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  GitBranch,
  ExternalLink,
  Copy,
  Check,
  MessageSquare,
  Clock
} from 'lucide-react';
import { api } from '../services/api';
import { EmailDetail, CrossEmailIntelligence } from '../types';
import {
  formatDate,
  formatDateTime,
  formatRelativeTime,
  getPriorityBadge,
  getCategoryBadge,
  getRelationshipBadge,
  getValidationBadge
} from '../utils/formatters';

const PROCESSING_STEPS = [
  'Reading email content and transmission headers',
  'Analyzing context & institutional sender hierarchy',
  'Detecting dynamic operational task cues',
  'Extracting & normalizing temporal expressions (anchored to arrival date)',
  'Formulating action-deadline relational edges (DUE_ON, PREPARE_BEFORE)',
  'Extracting meeting details, venues, and preparation requirements',
  'Evaluating context-aware multi-factor priority score',
  'Synthesizing structured academic executive summary',
  'Executing bidirectional source-sentence evidence grounding & validation',
  'Intelligence verified & persisted'
];

export const EmailDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const emailId = parseInt(id || '0', 10);
  const navigate = useNavigate();

  const [email, setEmail] = useState<EmailDetail | null>(null);
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [crossIntel, setCrossIntel] = useState<CrossEmailIntelligence | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // AI Analysis Stepper States
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [showEvidenceDrawer, setShowEvidenceDrawer] = useState(true);
  const [showCrossIntel, setShowCrossIntel] = useState(true);
  const [copiedReply, setCopiedReply] = useState(false);
  const [copiedSummary, setCopiedSummary] = useState(false);

  const loadEmailData = async () => {
    if (!emailId) return;
    try {
      setLoading(true);
      setError(null);
      const [data, intelRes, user] = await Promise.all([
        api.getEmailById(emailId),
        api.getCrossEmailIntelligence(emailId).catch(() => ({ success: false, data: null })),
        api.getCurrentUser().catch(() => null)
      ]);
      setEmail(data);
      if (user) setCurrentUser(user);
      if (intelRes && intelRes.data) {
        setCrossIntel(intelRes.data);
      }
      if (data && !data.is_read) {
        api.markEmailAsRead(emailId).catch(() => {});
      }
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve email details');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEmailData();
  }, [emailId]);

  // Handle Triggering AI Orchestration with Sequential Animation
  const handleAnalyze = async (forceRefresh: boolean = false) => {
    if (!emailId) return;
    try {
      setIsAnalyzing(true);
      setCurrentStepIndex(0);

      // Start asynchronous step sequence animation
      const interval = setInterval(() => {
        setCurrentStepIndex((prev) => {
          if (prev < PROCESSING_STEPS.length - 2) {
            return prev + 1;
          }
          return prev;
        });
      }, 350);

      await api.analyzeEmail(emailId, forceRefresh);

      clearInterval(interval);
      setCurrentStepIndex(PROCESSING_STEPS.length - 1);

      // Brief pause to allow evaluator to see "Complete"
      setTimeout(async () => {
        setIsAnalyzing(false);
        await loadEmailData();
      }, 500);
    } catch (err: any) {
      setIsAnalyzing(false);
      alert(`AI Orchestration failed: ${err.message}`);
    }
  };

  // Toggle Action Item completion
  const handleToggleAction = async (actionId: number, currentCompleted: boolean) => {
    try {
      const updated = await api.updateActionItem(actionId, { completed: !currentCompleted });
      setEmail((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          action_items: prev.action_items.map((a) => (a.id === actionId ? updated : a))
        };
      });
    } catch (err) {
      console.error('Failed to update action:', err);
    }
  };

  const handleCopyReply = (replyText?: string | null) => {
    const textToCopy = replyText || email?.analysis?.suggested_reply;
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopiedReply(true);
      setTimeout(() => setCopiedReply(false), 2500);
    }
  };

  const handleCopySummary = (summaryText?: string | null) => {
    const textToCopy = summaryText || email?.analysis?.summary;
    if (textToCopy) {
      navigator.clipboard.writeText(textToCopy);
      setCopiedSummary(true);
      setTimeout(() => setCopiedSummary(false), 2500);
    }
  };

  if (loading) {
    return (
      <div className="h-[80vh] flex items-center justify-center">
        <div className="text-center space-y-3">
          <RotateCw className="w-8 h-8 text-indigo-600 animate-spin mx-auto" />
          <p className="text-xs text-slate-500 font-medium">Loading email intelligence...</p>
        </div>
      </div>
    );
  }

  if (error || !email) {
    return (
      <div className="p-8 text-center bg-white rounded-xl border border-slate-200 max-w-md mx-auto my-12">
        <AlertTriangle className="w-10 h-10 text-rose-500 mx-auto mb-2" />
        <h3 className="text-sm font-semibold text-slate-800">Email Not Found in Active Account</h3>
        <p className="text-xs text-slate-500 mt-1 mb-4 leading-relaxed">
          {error?.includes('404') || error?.includes('not found')
            ? 'This email either does not exist or belongs to another user account. Each account maintains strict inbox isolation.'
            : (error || 'This email record could not be found in your inbox.')}
        </p>
        <div className="flex items-center justify-center space-x-3">
          <button
            onClick={loadEmailData}
            className="px-4 py-2 bg-slate-100 text-slate-700 rounded-lg text-xs font-semibold hover:bg-slate-200 transition-all"
          >
            Try Again
          </button>
          <button
            onClick={() => navigate('/inbox')}
            className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-all shadow-sm"
          >
            Back to Inbox
          </button>
        </div>
      </div>
    );
  }

  const analysis = email.analysis;
  const priorityBadge = analysis ? getPriorityBadge(analysis.priority) : null;
  const categoryBadge = analysis ? getCategoryBadge(analysis.category) : null;

  return (
    <div className="space-y-4">
      {/* Top Navigation & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-200">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center space-x-1.5 text-xs font-medium text-slate-600 hover:text-slate-900 transition-all self-start"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Correspondence</span>
        </button>

        <div className="flex items-center space-x-3">
          {analysis ? (
            <button
              onClick={() => handleAnalyze(true)}
              disabled={isAnalyzing}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 hover:bg-indigo-100 rounded-lg transition-all"
            >
              <RotateCw className={`w-3.5 h-3.5 ${isAnalyzing ? 'animate-spin' : ''}`} />
              <span>Re-analyze with AI</span>
            </button>
          ) : (
            <button
              onClick={() => handleAnalyze(false)}
              disabled={isAnalyzing}
              className="inline-flex items-center space-x-2 px-4 py-2 text-xs font-semibold text-white bg-indigo-600 hover:bg-indigo-700 shadow-sm shadow-indigo-500/30 rounded-lg transition-all"
            >
              <Sparkles className="w-4 h-4 text-indigo-200" />
              <span>Analyze with AI</span>
            </button>
          )}
        </div>
      </div>

      {/* AI Processing Stepper Modal / Banner */}
      {isAnalyzing && (
        <div className="bg-slate-900 text-white p-5 rounded-xl border border-slate-800 shadow-xl space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Sparkles className="w-5 h-5 text-indigo-400 animate-pulse" />
              <h3 className="text-sm font-semibold tracking-tight">AI Agent Orchestration in Progress...</h3>
            </div>
            <span className="text-xs text-indigo-300 font-mono">
              Step {currentStepIndex + 1} of {PROCESSING_STEPS.length}
            </span>
          </div>

          <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
            <div
              className="bg-indigo-500 h-full transition-all duration-300 ease-out"
              style={{ width: `${((currentStepIndex + 1) / PROCESSING_STEPS.length) * 100}%` }}
            />
          </div>

          <div className="p-3 bg-slate-950/70 rounded-lg border border-slate-800/80">
            <p className="text-xs text-indigo-200 font-medium flex items-center">
              <RotateCw className="w-3.5 h-3.5 mr-2 animate-spin text-indigo-400 flex-shrink-0" />
              {PROCESSING_STEPS[currentStepIndex]}
            </p>
          </div>
        </div>
      )}

      {/* CENTERPIECE: Two-Panel Grid Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* LEFT PANEL: Original Email (5 Columns on Large Displays) */}
        <div className="lg:col-span-5 bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden flex flex-col">
          {/* Email Header */}
          <div className="p-5 border-b border-slate-100 bg-slate-50/50 space-y-3">
            <div className="flex items-start justify-between">
              <div className="flex items-center space-x-3">
                <div className="w-9 h-9 rounded-full bg-slate-200 flex items-center justify-center text-slate-700 font-bold text-xs">
                  {email.sender.slice(0, 2).toUpperCase()}
                </div>
                <div>
                  <h3 className="text-xs font-bold text-slate-900 leading-tight">{email.sender}</h3>
                  <p className="text-[11px] text-slate-500">To: {email.recipient}</p>
                </div>
              </div>
              <span className="text-[11px] text-slate-400 font-medium">
                {formatDateTime(email.received_at)}
              </span>
            </div>

            <div>
              <h2 className="text-sm font-semibold text-slate-900 leading-snug">{email.subject}</h2>
            </div>
          </div>

          {/* Email Body Content */}
          <div className="p-6 overflow-y-auto max-h-[650px] text-xs leading-relaxed text-slate-700 whitespace-pre-line font-sans select-text">
            {email.body}
          </div>

          <div className="p-3 bg-slate-50 border-t border-slate-100 text-[11px] text-slate-400 text-right">
            Raw email record • Immutable ingestion
          </div>
        </div>

        {/* RIGHT PANEL: AI Intelligence (7 Columns on Large Displays) */}
        <div className="lg:col-span-7 space-y-5">
          {!analysis && !isAnalyzing ? (
            /* Unanalyzed Empty State */
            <div className="p-12 text-center bg-white rounded-xl border border-dashed border-slate-300">
              <Sparkles className="w-12 h-12 text-indigo-400 mx-auto mb-3" />
              <h3 className="text-sm font-semibold text-slate-800">Email Not Yet Analyzed</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto mt-1 mb-5">
                Execute the multi-agent AI pipeline to extract executive summaries, context-aware priorities,
                normalized deadlines, meeting venue data, and grounded evidence.
              </p>
              <button
                onClick={() => handleAnalyze(false)}
                className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-semibold shadow-sm transition-all inline-flex items-center space-x-2"
              >
                <Sparkles className="w-4 h-4 text-indigo-200" />
                <span>Trigger AI Intelligence Pipeline</span>
              </button>
            </div>
          ) : analysis ? (
            /* Structured AI Intelligence Output */
            <div className="space-y-4">
              {/* Provenance Badge */}
              <div className="p-3 bg-slate-900 text-white rounded-xl border border-slate-800 flex items-center justify-between text-xs">
                <div className="flex items-center space-x-2">
                  <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                  <span className="font-semibold text-slate-100">AI Intelligence Provenance:</span>
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800/60 font-semibold">
                    {currentUser?.provider_type === 'gmail' ? 'Live LLM Engine' : 'Deterministic Mock AI Engine'}
                  </span>
                </div>
                <span className="text-[10px] text-slate-400 hidden sm:inline">
                  {currentUser?.provider_type === 'gmail' ? 'Live Gmail Account' : 'Pre-loaded Academic Benchmark'}
                </span>
              </div>

              {/* Card 1: Executive Summary */}
              <div className="p-5 bg-gradient-to-br from-indigo-50/70 via-white to-slate-50/50 rounded-xl border border-indigo-100 shadow-sm space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-indigo-900 uppercase tracking-wider flex items-center">
                    <FileText className="w-3.5 h-3.5 mr-1.5 text-indigo-600" />
                    Executive Summary
                  </span>
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] text-slate-400 font-mono">
                      ~1 min read • {formatRelativeTime(analysis.processed_at)}
                    </span>
                    <button
                      onClick={() => handleCopySummary(analysis.summary)}
                      className="inline-flex items-center space-x-1 px-2.5 py-1 text-[11px] font-semibold text-indigo-700 hover:text-indigo-900 bg-white border border-indigo-200 rounded-md shadow-xs transition-all hover:bg-indigo-50"
                      title="Copy Executive Summary"
                    >
                      {copiedSummary ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3 text-indigo-600" />}
                      <span>{copiedSummary ? 'Copied!' : 'Copy'}</span>
                    </button>
                  </div>
                </div>
                <p className="text-xs font-medium text-slate-800 leading-relaxed bg-white p-4 rounded-lg border border-indigo-100/70 select-text">
                  {analysis.summary}
                </p>
              </div>

              {/* Card 2: Category & Context-Aware Priority */}
              <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                      Classification:
                    </span>
                    {categoryBadge && (
                      <span className={`text-xs font-semibold px-2.5 py-0.5 rounded-full ${categoryBadge.bg} ${categoryBadge.text}`}>
                        {analysis.category}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">
                      Urgency Level:
                    </span>
                    {priorityBadge && (
                      <span
                        className={`text-xs font-bold px-3 py-0.5 rounded-full border ${priorityBadge.bg} ${priorityBadge.text} ${priorityBadge.border}`}
                      >
                        {priorityBadge.label} PRIORITY
                      </span>
                    )}
                  </div>
                </div>

                {/* Explainable Priority Reason Callout */}
                <div className="p-3 bg-slate-50 rounded-lg border border-slate-200/80 text-xs space-y-1">
                  <span className="text-[11px] font-semibold text-slate-700 flex items-center">
                    <HelpCircle className="w-3.5 h-3.5 mr-1 text-slate-500" />
                    Priority Justification (Transparent Multi-Factor Reasoning):
                  </span>
                  <p className="text-slate-600 italic leading-normal pl-4 border-l-2 border-indigo-300">
                    "{analysis.priority_reason}"
                  </p>
                </div>
              </div>

              {/* Dedicated Extracted Deadlines Section */}
              {((email.action_items && email.action_items.some((a) => Boolean(a.due_date))) || analysis.deadline_date) && (
                <div className="p-5 bg-white rounded-xl border border-amber-200 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-bold text-amber-950 uppercase tracking-wider flex items-center">
                      <Clock className="w-3.5 h-3.5 mr-1.5 text-amber-600" />
                      Extracted Deadlines &amp; Milestones
                    </span>
                    <span className="text-[10px] text-amber-800 font-medium bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                      Anchored to arrival date
                    </span>
                  </div>

                  <div className="space-y-2">
                    {email.action_items?.filter((a) => Boolean(a.due_date)).map((act) => {
                      const relBadge = getRelationshipBadge(act.relationship_type);
                      return (
                        <div
                          key={act.id}
                          className="p-3 bg-amber-50/30 rounded-lg border border-amber-100 flex items-start justify-between gap-3 text-xs"
                        >
                          <div className="space-y-1 flex-1">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <span className="font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200 text-xs">
                                {formatDate(act.due_date)}
                              </span>
                              <span className={`px-2 py-0.5 rounded font-medium text-[10px] ${relBadge.bg} ${relBadge.text}`}>
                                {relBadge.label}
                              </span>
                              {act.target_event && (
                                <span className="text-slate-600 bg-white px-2 py-0.5 rounded border border-slate-200 text-[10px]">
                                  {act.target_event}
                                </span>
                              )}
                            </div>
                            <p className={`font-medium ${act.completed ? 'line-through text-slate-400' : 'text-slate-800'}`}>
                              {act.description}
                            </p>
                          </div>
                          <button
                            onClick={() => handleToggleAction(act.id, act.completed)}
                            className="mt-0.5 text-slate-400 hover:text-emerald-600 transition-all flex-shrink-0"
                            title={act.completed ? 'Mark pending' : 'Mark completed'}
                          >
                            {act.completed ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                            ) : (
                              <Circle className="w-4 h-4 text-slate-300 hover:text-emerald-500" />
                            )}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Card: Context-Aware Smart Reply Suggestions (Stage 21) */}
              {analysis.reply_expected && analysis.suggested_reply && (
                <div className="p-5 bg-gradient-to-br from-indigo-50/70 via-white to-blue-50/50 rounded-xl border border-indigo-200 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <MessageSquare className="w-4 h-4 text-indigo-600" />
                      <span className="text-[11px] font-bold text-indigo-950 uppercase tracking-wider">
                        Smart Reply Suggestion
                      </span>
                      <span className="text-[10px] font-semibold bg-indigo-100 text-indigo-800 px-2 py-0.5 rounded-full">
                        AI Draft
                      </span>
                    </div>
                    {analysis.reply_reason && (
                      <span className="text-[10px] font-medium text-indigo-700 bg-indigo-50 border border-indigo-200 px-2 py-0.5 rounded">
                        Intent: {analysis.reply_reason}
                      </span>
                    )}
                  </div>

                  <div className="relative bg-white p-4 rounded-lg border border-indigo-100 shadow-xs">
                    <p className="text-xs text-slate-800 whitespace-pre-line leading-relaxed font-sans select-text">
                      {analysis.suggested_reply}
                    </p>
                  </div>

                  <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={() => handleCopyReply(analysis.suggested_reply)}
                        className={`inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-xs ${
                          copiedReply
                            ? 'bg-emerald-600 text-white'
                            : 'bg-indigo-600 text-white hover:bg-indigo-700'
                        }`}
                      >
                        {copiedReply ? (
                          <>
                            <Check className="w-3.5 h-3.5" />
                            <span>Copied to Clipboard!</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copy Reply</span>
                          </>
                        )}
                      </button>

                      <button
                        onClick={() => handleAnalyze(true)}
                        disabled={isAnalyzing}
                        className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 transition-all"
                      >
                        <RotateCw className={`w-3 h-3 text-slate-500 ${isAnalyzing ? 'animate-spin' : ''}`} />
                        <span>Regenerate</span>
                      </button>
                    </div>

                    <span className="text-[10px] text-slate-400 italic">
                      Read-only draft • No emails are sent automatically
                    </span>
                  </div>
                </div>
              )}

              {/* Card 3: Action Items & Semantic Deadline Relationships (Stage 8) */}
              {email.action_items && email.action_items.length > 0 && (
                <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider flex items-center">
                      <CheckSquare className="w-3.5 h-3.5 mr-1.5 text-emerald-600" />
                      Action Items & Relational Obligations ({email.action_items.length})
                    </span>
                    <span className="text-[10px] text-slate-400">Click to toggle completion</span>
                  </div>

                  <div className="space-y-2.5">
                    {email.action_items.map((act) => {
                      const relBadge = getRelationshipBadge(act.relationship_type);
                      return (
                        <div
                          key={act.id}
                          className={`p-3 rounded-lg border transition-all ${
                            act.completed
                              ? 'bg-slate-50/70 border-slate-200 text-slate-400'
                              : 'bg-white border-slate-200 hover:border-indigo-300 shadow-xs'
                          }`}
                        >
                          <div className="flex items-start space-x-3">
                            <button
                              onClick={() => handleToggleAction(act.id, act.completed)}
                              className="mt-0.5 text-slate-400 hover:text-emerald-600 transition-all flex-shrink-0"
                            >
                              {act.completed ? (
                                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                              ) : (
                                <Circle className="w-4 h-4 text-slate-300 hover:text-emerald-500" />
                              )}
                            </button>

                            <div className="flex-1 space-y-1.5">
                              <p className={`text-xs ${act.completed ? 'line-through text-slate-400' : 'text-slate-900 font-medium'}`}>
                                {act.description}
                              </p>

                              {/* Relational Edge Info */}
                              <div className="flex flex-wrap items-center gap-2 text-[11px]">
                                <span className={`px-2 py-0.5 rounded font-medium ${relBadge.bg} ${relBadge.text}`}>
                                  {relBadge.label}
                                </span>

                                {act.due_date && (
                                  <span className="font-semibold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-200">
                                    {formatDate(act.due_date)}
                                  </span>
                                )}

                                {act.target_event && (
                                  <span className="text-slate-600 bg-slate-100 px-2 py-0.5 rounded truncate max-w-[200px]">
                                    Event: {act.target_event}
                                  </span>
                                )}
                              </div>

                              {act.relationship_reason && (
                                <p className="text-[11px] text-slate-500 italic">
                                  {act.relationship_reason}
                                </p>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Card 4: Meeting Intelligence */}
              {email.meetings && email.meetings.length > 0 && (
                <div className="p-5 bg-white rounded-xl border border-slate-200 shadow-sm space-y-3">
                  <span className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider flex items-center">
                    <Calendar className="w-3.5 h-3.5 mr-1.5 text-indigo-600" />
                    Scheduled Meeting Details
                  </span>

                  {email.meetings.map((m) => (
                    <div key={m.id} className="p-3.5 bg-indigo-50/40 rounded-lg border border-indigo-100/70 space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="text-xs font-bold text-slate-900">{m.title}</h4>
                        <span className="text-xs font-semibold text-indigo-700 bg-white px-2 py-0.5 rounded border border-indigo-200 shadow-xs">
                          {formatDate(m.meeting_date)} {m.meeting_time ? `@ ${m.meeting_time}` : ''}
                        </span>
                      </div>

                      {m.location && (
                        <div className="flex items-center text-xs text-slate-700">
                          <MapPin className="w-3.5 h-3.5 mr-1.5 text-indigo-500 flex-shrink-0" />
                          <span className="font-medium">{m.location}</span>
                        </div>
                      )}

                      {m.preparation && (
                        <div className="text-[11px] text-amber-900 bg-amber-50 p-2 rounded border border-amber-200">
                          <span className="font-semibold">Prerequisite Checklist:</span> {m.preparation}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}

              {/* Card 5: Extracted Academic Entities */}
              {email.entities && email.entities.length > 0 && (
                <div className="p-4 bg-white rounded-xl border border-slate-200 shadow-sm space-y-2">
                  <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider flex items-center">
                    <Tag className="w-3.5 h-3.5 mr-1.5 text-slate-400" />
                    Important Academic Entities
                  </span>
                  <div className="flex flex-wrap gap-2">
                    {email.entities.map((ent, idx) => (
                      <span
                        key={idx}
                        className="inline-flex items-center text-[11px] bg-slate-100 text-slate-700 px-2 py-0.5 rounded-md border border-slate-200"
                      >
                        <span className="text-[10px] text-slate-400 uppercase mr-1">{ent.entity_type}:</span>
                        <span className="font-medium">{ent.entity_value}</span>
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Card 6: Grounded Source Evidence Drawer (Stage 9) */}
              {analysis.evidences && analysis.evidences.length > 0 && (
                <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
                  <button
                    onClick={() => setShowEvidenceDrawer(!showEvidenceDrawer)}
                    className="w-full px-5 py-3.5 bg-slate-50/70 border-b border-slate-200 flex items-center justify-between text-left hover:bg-slate-100/60 transition-all"
                  >
                    <div className="flex items-center space-x-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      <span className="text-xs font-semibold text-slate-800">
                        Audit & Verification Evidence ({analysis.evidences.length} Anchored Citations)
                      </span>
                    </div>
                    {showEvidenceDrawer ? (
                      <ChevronUp className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    )}
                  </button>

                  {showEvidenceDrawer && (
                    <div className="p-4 space-y-3 divide-y divide-slate-100">
                      {analysis.evidences.map((ev, i) => {
                        const valBadge = getValidationBadge(ev.validation_status);
                        return (
                          <div key={i} className={`pt-3 first:pt-0 space-y-1.5`}>
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                                {ev.field_name}
                              </span>
                              <div className="flex items-center space-x-2">
                                <span
                                  className={`text-[10px] font-semibold px-2 py-0.5 rounded border ${valBadge.bg} ${valBadge.text} ${valBadge.border}`}
                                >
                                  {ev.validation_status}
                                </span>
                                <span className="text-[10px] text-slate-400 font-mono">
                                  {Math.round(ev.confidence * 100)}% Conf.
                                </span>
                              </div>
                            </div>

                            <p className="text-xs text-slate-800 font-medium bg-slate-50 p-2.5 rounded border border-slate-200/60">
                              "{ev.source_text}"
                            </p>

                            <div className="flex items-center justify-between text-[10px] text-slate-400 font-mono">
                              <span>
                                Span Offset: [{ev.char_start ?? '—'} : {ev.char_end ?? '—'}]
                              </span>
                              <span>Method: {ev.grounding_method || 'EXACT_SPAN'}</span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}

              {/* Cross-Email Intelligence & Thread Context (Stage 14) */}
              <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                  <div className="flex items-center space-x-2">
                    <GitBranch className="w-4 h-4 text-indigo-600" />
                    <h3 className="text-sm font-semibold text-slate-900">
                      Cross-Email Intelligence &amp; Thread Context
                    </h3>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-50 text-indigo-700 border border-indigo-200">
                      Stage 14
                    </span>
                    <button
                      onClick={() => setShowCrossIntel(!showCrossIntel)}
                      className="p-1 hover:bg-slate-100 rounded text-slate-400 hover:text-slate-600"
                    >
                      {showCrossIntel ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {showCrossIntel && (
                  <div className="space-y-4">
                    {/* Thread Context Summary */}
                    {crossIntel?.insights && crossIntel.insights.length > 0 && (
                      <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs text-slate-700 space-y-1">
                        {crossIntel.insights.map((ins, idx) => (
                          <div key={idx} className="flex items-start space-x-2">
                            <span className="text-indigo-600 font-bold">&bull;</span>
                            <span>{ins}</span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Related Emails */}
                    {crossIntel?.related_emails && crossIntel.related_emails.length > 0 ? (
                      <div className="space-y-2">
                        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                          Correlated Communications ({crossIntel.related_emails.length})
                        </span>
                        <div className="space-y-2">
                          {crossIntel.related_emails.map((rel) => (
                            <div
                              key={rel.id}
                              className="p-3 bg-slate-50/70 hover:bg-indigo-50/40 rounded-lg border border-slate-200/80 transition-all flex items-start justify-between gap-2"
                            >
                              <div className="space-y-1 min-w-0">
                                <div className="flex items-center space-x-2">
                                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-100 text-indigo-800">
                                    {rel.relationship_type.replace('_', ' ')}
                                  </span>
                                  <span className="text-[10px] text-slate-400 font-mono">
                                    {Math.round(rel.relevance_score * 100)}% Match
                                  </span>
                                </div>
                                <h4 className="text-xs font-semibold text-slate-800 truncate">
                                  {rel.subject}
                                </h4>
                                <p className="text-[11px] text-slate-500">
                                  From: {rel.sender} &bull; {formatRelativeTime(rel.received_at || '')}
                                </p>
                                {rel.relationship_reasons && (
                                  <div className="flex flex-wrap gap-1 pt-1">
                                    {rel.relationship_reasons.map((r, i) => (
                                      <span key={i} className="text-[9px] px-1.5 py-0.5 bg-white border border-slate-200 text-slate-600 rounded">
                                        {r}
                                      </span>
                                    ))}
                                  </div>
                                )}
                              </div>
                              <button
                                onClick={() => navigate(`/emails/${rel.id}`)}
                                className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-white rounded border border-transparent hover:border-slate-200 transition-all flex-shrink-0"
                                title="Open Correlated Email"
                              >
                                <ExternalLink className="w-3.5 h-3.5" />
                              </button>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <div className="p-4 bg-slate-50 rounded-lg border border-slate-200/60 text-center text-xs text-slate-500">
                        No directly correlated preceding or succeeding email threads detected in the inbox.
                      </div>
                    )}

                    {/* Timeline Progression if multi-event */}
                    {crossIntel?.timeline && crossIntel.timeline.length > 1 && (
                      <div className="space-y-2 pt-2 border-t border-slate-100">
                        <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                          Cross-Communication Chronological Timeline
                        </span>
                        <div className="space-y-1.5">
                          {crossIntel.timeline.map((item, idx) => (
                            <div
                              key={idx}
                              className={`p-2 rounded text-xs flex items-center justify-between border ${
                                item.is_current ? 'bg-indigo-50/70 border-indigo-200 font-medium' : 'bg-slate-50 border-slate-200/60'
                              }`}
                            >
                              <div className="flex items-center space-x-2 min-w-0">
                                <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded uppercase ${
                                  item.type === 'MEETING' ? 'bg-purple-100 text-purple-800' :
                                  item.type === 'DEADLINE' ? 'bg-amber-100 text-amber-800' :
                                  'bg-slate-200 text-slate-700'
                                }`}>
                                  {item.type}
                                </span>
                                <span className="truncate text-slate-800 text-[11px]">{item.title}</span>
                              </div>
                              <span className="text-[10px] font-mono text-slate-500 flex-shrink-0 ml-2">
                                {item.date} {item.time ? `@ ${item.time}` : ''}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
