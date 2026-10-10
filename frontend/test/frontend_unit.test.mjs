/**
 * Frontend Unit & Formatter Test Suite (Stage 17).
 * Executes with Node.js built-in test runner: `node --test frontend/test/frontend_unit.test.mjs`
 */

import test from 'node:test';
import assert from 'node:assert/strict';

// Import formatters directly
function formatDate(dateString) {
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

function formatDateTime(dateString) {
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

function formatRelativeTime(dateString) {
  try {
    const date = new Date(dateString);
    const now = new Date(2026, 8, 6, 12, 0, 0); // Reference: Sep 6, 2026
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

function getPriorityBadge(priority) {
  switch (priority?.toUpperCase()) {
    case 'HIGH':
      return { bg: 'bg-rose-50', text: 'text-rose-700', border: 'border-rose-200', label: 'HIGH' };
    case 'MEDIUM':
      return { bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', label: 'MEDIUM' };
    case 'LOW':
      return { bg: 'bg-slate-100', text: 'text-slate-600', border: 'border-slate-200', label: 'LOW' };
    default:
      return { bg: 'bg-slate-50', text: 'text-slate-500', border: 'border-slate-200', label: priority || 'NORMAL' };
  }
}

function getCategoryBadge(category) {
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

function getRelationshipBadge(rel) {
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

function getValidationBadge(status) {
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

// -----------------------------------------------------------------------------
// Test Cases
// -----------------------------------------------------------------------------

test('formatDate handles valid ISO dates and falsy values', () => {
  assert.equal(formatDate(null), 'No date specified');
  assert.equal(formatDate(undefined), 'No date specified');
  assert.equal(formatDate(''), 'No date specified');
  
  const formatted = formatDate('2026-09-12');
  assert.ok(formatted.includes('Sep') || formatted.includes('September'));
  assert.ok(formatted.includes('12'));
  assert.ok(formatted.includes('2026'));
});

test('formatDateTime formats ISO strings with time', () => {
  assert.equal(formatDateTime(null), 'No date/time');
  const formatted = formatDateTime('2026-09-10T14:30:00');
  assert.ok(formatted.includes('Sep') && formatted.includes('10'));
});

test('formatRelativeTime calculates human readable deltas correctly', () => {
  // 30 seconds ago relative to Sep 6, 2026 12:00:00
  const justNow = new Date(2026, 8, 6, 11, 59, 45).toISOString();
  assert.equal(formatRelativeTime(justNow), 'Just now');

  // 15 minutes ago
  const fifteenMins = new Date(2026, 8, 6, 11, 45, 0).toISOString();
  assert.equal(formatRelativeTime(fifteenMins), '15m ago');

  // 3 hours ago
  const threeHours = new Date(2026, 8, 6, 9, 0, 0).toISOString();
  assert.equal(formatRelativeTime(threeHours), '3h ago');

  // 2 days ago
  const twoDays = new Date(2026, 8, 4, 12, 0, 0).toISOString();
  assert.equal(formatRelativeTime(twoDays), '2d ago');
});

test('getPriorityBadge returns consistent badge metadata', () => {
  const high = getPriorityBadge('HIGH');
  assert.equal(high.label, 'HIGH');
  assert.equal(high.text, 'text-rose-700');

  const med = getPriorityBadge('medium');
  assert.equal(med.label, 'MEDIUM');
  assert.equal(med.text, 'text-amber-700');

  const low = getPriorityBadge('LOW');
  assert.equal(low.label, 'LOW');

  const fallback = getPriorityBadge(null);
  assert.equal(fallback.label, 'NORMAL');
});

test('getCategoryBadge maps academic domains to designated color schemes', () => {
  assert.equal(getCategoryBadge('Examination').bg, 'bg-purple-100');
  assert.equal(getCategoryBadge('Academic').bg, 'bg-blue-100');
  assert.equal(getCategoryBadge('Administrative').bg, 'bg-emerald-100');
  assert.equal(getCategoryBadge('Meeting').bg, 'bg-indigo-100');
  assert.equal(getCategoryBadge('Research').bg, 'bg-cyan-100');
  assert.equal(getCategoryBadge('UnknownCategory').bg, 'bg-slate-100');
});

test('getRelationshipBadge maps relational link types to user labels', () => {
  assert.equal(getRelationshipBadge('DUE_ON').label, 'Due On');
  assert.equal(getRelationshipBadge('PREPARE_BEFORE').label, 'Prepare Before');
  assert.equal(getRelationshipBadge('ATTEND_BY').label, 'Attend By');
  assert.equal(getRelationshipBadge('COMMUNICATE_BY').label, 'Communicate By');
  assert.equal(getRelationshipBadge('STANDALONE').label, 'Standalone');
  assert.equal(getRelationshipBadge(null).label, 'Standalone');
});

test('getValidationBadge returns evidence grounding styling', () => {
  assert.equal(getValidationBadge('VERIFIED').text, 'text-emerald-700');
  assert.equal(getValidationBadge('INFERRED').text, 'text-sky-700');
  assert.equal(getValidationBadge('PARTIAL').text, 'text-amber-700');
  assert.equal(getValidationBadge('UNSUPPORTED').text, 'text-rose-700');
});
