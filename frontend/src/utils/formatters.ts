import { PriorityLevel, AcademicCategory, RelationshipType, ValidationStatus } from '../types';

export function formatDate(dateString?: string | null): string {
  if (!dateString) return 'No date specified';
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    });
  } catch {
    return dateString;
  }
}

export function formatDateTime(dateString?: string | null): string {
  if (!dateString) return 'No date/time';
  try {
    const d = new Date(dateString);
    if (isNaN(d.getTime())) return dateString;
    return d.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateString;
  }
}

export function formatRelativeTime(dateString: string): string {
  try {
    const date = new Date(dateString);
    const now = new Date(2026, 8, 6, 12, 0, 0); // Anchored reference or current date
    const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

    if (diffInSeconds < 60) return 'Just now';
    if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
    if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
    if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;
    return formatDate(dateString);
  } catch {
    return dateString;
  }
}

export function getPriorityBadge(priority?: PriorityLevel | string | null): {
  bg: string;
  text: string;
  border: string;
  label: string;
} {
  switch (priority?.toUpperCase()) {
    case 'HIGH':
      return {
        bg: 'bg-rose-50',
        text: 'text-rose-700',
        border: 'border-rose-200',
        label: 'HIGH'
      };
    case 'MEDIUM':
      return {
        bg: 'bg-amber-50',
        text: 'text-amber-700',
        border: 'border-amber-200',
        label: 'MEDIUM'
      };
    case 'LOW':
      return {
        bg: 'bg-slate-100',
        text: 'text-slate-600',
        border: 'border-slate-200',
        label: 'LOW'
      };
    default:
      return {
        bg: 'bg-slate-50',
        text: 'text-slate-500',
        border: 'border-slate-200',
        label: priority || 'NORMAL'
      };
  }
}

export function getCategoryBadge(category?: AcademicCategory | string | null): {
  bg: string;
  text: string;
} {
  switch (category) {
    case 'Examination':
      return { bg: 'bg-purple-100', text: 'text-purple-800' };
    case 'Academic':
      return { bg: 'bg-blue-100', text: 'text-blue-800' };
    case 'Administrative':
      return { bg: 'bg-emerald-100', text: 'text-emerald-800' };
    case 'Meeting':
      return { bg: 'bg-indigo-100', text: 'text-indigo-800' };
    case 'Student':
      return { bg: 'bg-teal-100', text: 'text-teal-800' };
    case 'Research':
      return { bg: 'bg-cyan-100', text: 'text-cyan-800' };
    case 'Placement':
      return { bg: 'bg-amber-100', text: 'text-amber-800' };
    default:
      return { bg: 'bg-slate-100', text: 'text-slate-800' };
  }
}

export function getRelationshipBadge(rel?: RelationshipType | string | null): {
  bg: string;
  text: string;
  label: string;
} {
  switch (rel?.toUpperCase()) {
    case 'DUE_ON':
      return { bg: 'bg-rose-100', text: 'text-rose-800', label: 'Due On' };
    case 'PREPARE_BEFORE':
      return { bg: 'bg-indigo-100', text: 'text-indigo-800', label: 'Prepare Before' };
    case 'ATTEND_BY':
      return { bg: 'bg-blue-100', text: 'text-blue-800', label: 'Attend By' };
    case 'COMMUNICATE_BY':
      return { bg: 'bg-amber-100', text: 'text-amber-800', label: 'Communicate By' };
    default:
      return { bg: 'bg-slate-100', text: 'text-slate-700', label: 'Standalone' };
  }
}

export function getValidationBadge(status?: ValidationStatus | string | null): {
  bg: string;
  text: string;
  border: string;
} {
  switch (status?.toUpperCase()) {
    case 'VERIFIED':
      return { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' };
    case 'INFERRED':
      return { bg: 'bg-sky-50', text: 'text-sky-700', border: 'border-sky-200' };
    case 'PARTIAL':
      return { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200' };
    case 'UNSUPPORTED':
      return { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200' };
    default:
      return { bg: 'bg-slate-50', text: 'text-slate-600', border: 'border-slate-200' };
  }
}

export function getDeadlineStatusBadge(status?: string | null): {
  bg: string;
  text: string;
  border: string;
  label: string;
} {
  switch (status?.toUpperCase()) {
    case 'DUE_TODAY':
      return { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', label: 'Due Today' };
    case 'UPCOMING':
      return { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', label: 'Upcoming' };
    case 'EXPIRED':
      return { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-200', label: 'Past Deadline' };
    default:
      return { bg: 'bg-indigo-50', text: 'text-indigo-700', border: 'border-indigo-200', label: status || 'Scheduled' };
  }
}
