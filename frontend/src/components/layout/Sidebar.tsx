import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Inbox,
  AlertTriangle,
  Clock,
  Calendar,
  CheckSquare,
  Settings,
  ShieldCheck,
  Cpu,
  Mail
} from 'lucide-react';
import { DashboardMetrics } from '../../types';

interface SidebarProps {
  metrics?: DashboardMetrics | null;
}

export const Sidebar: React.FC<SidebarProps> = ({ metrics }) => {
  const navItems = [
    {
      name: 'Dashboard',
      path: '/',
      icon: LayoutDashboard,
      badge: null
    },
    {
      name: 'Smart Inbox',
      path: '/inbox',
      icon: Inbox,
      badge: metrics?.unread_emails ? metrics.unread_emails : null,
      badgeColor: 'bg-blue-600 text-white'
    },
    {
      name: 'Priority Inbox',
      path: '/priority',
      icon: AlertTriangle,
      badge: metrics?.high_priority_count ? metrics.high_priority_count : null,
      badgeColor: 'bg-rose-600 text-white'
    },
    {
      name: 'Deadlines',
      path: '/deadlines',
      icon: Clock,
      badge: metrics?.upcoming_deadlines_count ? metrics.upcoming_deadlines_count : null,
      badgeColor: 'bg-amber-600 text-white'
    },
    {
      name: 'Meetings',
      path: '/meetings',
      icon: Calendar,
      badge: metrics?.upcoming_meetings_count ? metrics.upcoming_meetings_count : null,
      badgeColor: 'bg-indigo-600 text-white'
    },
    {
      name: 'Action Items',
      path: '/action-items',
      icon: CheckSquare,
      badge: metrics?.pending_actions_count ? metrics.pending_actions_count : null,
      badgeColor: 'bg-emerald-600 text-white'
    },
    {
      name: 'Settings',
      path: '/settings',
      icon: Settings,
      badge: null
    }
  ];

  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col flex-shrink-0 border-r border-slate-800 select-none">
      {/* Brand Header */}
      <div className="h-16 px-6 flex items-center space-x-3 border-b border-slate-800 bg-slate-950/50">
        <div className="p-2 bg-indigo-600 rounded-lg text-white shadow-sm shadow-indigo-500/20">
          <Mail className="w-5 h-5" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-white tracking-tight">Faculty AI Agent</h1>
          <p className="text-[11px] text-slate-400 font-medium">Academic Intelligence</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
          Intelligence Feeds
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2.5 rounded-lg text-xs font-medium transition-all ${
                  isActive
                    ? 'bg-indigo-600/15 text-indigo-400 border border-indigo-500/20'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                }`
              }
            >
              <div className="flex items-center space-x-3">
                <Icon className="w-4 h-4 flex-shrink-0" />
                <span>{item.name}</span>
              </div>
              {item.badge !== null && item.badge !== undefined && (
                <span
                  className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full ${
                    item.badgeColor || 'bg-slate-700 text-slate-300'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </NavLink>
          );
        })}
      </nav>

      {/* System Status Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/40 text-[11px]">
        <div className="flex items-center justify-between mb-2">
          <span className="text-slate-400 flex items-center">
            <Cpu className="w-3.5 h-3.5 mr-1.5 text-indigo-400" />
            Engine Mode
          </span>
          <span className="px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300 font-mono text-[10px] border border-indigo-800/40">
            DETERMINISTIC
          </span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span className="flex items-center">
            <ShieldCheck className="w-3.5 h-3.5 mr-1.5 text-emerald-400" />
            Evidence Grounding
          </span>
          <span className="text-slate-300 font-medium text-[10px]">Source-Anchored</span>
        </div>
      </div>
    </aside>
  );
};
