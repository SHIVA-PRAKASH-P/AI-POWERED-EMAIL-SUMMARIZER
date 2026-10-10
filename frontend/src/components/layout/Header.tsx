import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, RotateCw, ChevronDown, Check, Shield, Plus } from 'lucide-react';
import { api } from '../../services/api';

interface HeaderProps {
  onRefresh?: () => void;
  isRefreshing?: boolean;
}

interface UserInfo {
  id: number;
  email: string;
  name: string;
  role: string;
  provider_type: string;
}

export const Header: React.FC<HeaderProps> = ({ onRefresh, isRefreshing = false }) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [currentUser, setCurrentUser] = useState<UserInfo | null>(null);
  const [users, setUsers] = useState<UserInfo[]>([]);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isSwitching, setIsSwitching] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    let mounted = true;
    const fetchAuthData = async () => {
      try {
        const [me, allUsers] = await Promise.all([
          api.getCurrentUser(),
          api.getRegisteredUsers()
        ]);
        if (mounted) {
          setCurrentUser(me);
          setUsers(allUsers);
        }
      } catch (err) {
        console.warn('Could not load user auth state:', err);
      }
    };
    fetchAuthData();

    const handleSessionChanged = () => {
      fetchAuthData();
    };
    window.addEventListener('auth-session-changed', handleSessionChanged);

    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      mounted = false;
      document.removeEventListener('mousedown', handleClickOutside);
      window.removeEventListener('auth-session-changed', handleSessionChanged);
    };
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      navigate(`/inbox?search=${encodeURIComponent(searchQuery.trim())}`);
    }
  };

  const handleSwitchUser = async (email: string) => {
    if (currentUser && currentUser.email === email) {
      setIsDropdownOpen(false);
      return;
    }
    try {
      setIsSwitching(true);
      await api.switchSession(email);
      setIsDropdownOpen(false);
      // Navigate to inbox if currently on an email detail page to avoid 404
      if (window.location.pathname.startsWith('/emails/')) {
        window.location.href = '/inbox';
      } else {
        window.location.reload();
      }
    } catch (err) {
      console.error('Failed to switch user:', err);
      setIsSwitching(false);
    }
  };

  const handleConnectAnotherAccount = async () => {
    try {
      setIsSwitching(true);
      const res = await api.getGmailConnectUrl(true);
      if (res && res.authorization_url) {
        window.location.href = res.authorization_url;
      }
    } catch (err: any) {
      alert(`Could not initiate Google OAuth: ${err.message}`);
      setIsSwitching(false);
    }
  };

  const isUser1 = currentUser?.id === 1 || !currentUser;
  const userInitials = currentUser?.name
    ? currentUser.name.split(' ').map(p => p[0]).join('').slice(0, 2).toUpperCase()
    : 'U1';

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between flex-shrink-0 relative z-30">
      {/* Search Bar */}
      <form onSubmit={handleSearchSubmit} className="flex-1 max-w-xl">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search across sender, subject, body, deadlines, tasks..."
            className="w-full pl-10 pr-4 py-2 text-xs bg-slate-50 border border-slate-200 rounded-lg text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 focus:border-indigo-500 transition-all"
          />
        </div>
      </form>

      {/* Action Controls & User Switcher */}
      <div className="flex items-center space-x-3.5 ml-6">
        {/* Accurate Environment / Provider Status Pill */}
        <div className="hidden lg:flex items-center">
          <span className={`text-[11px] font-semibold px-2.5 py-1 rounded-full border flex items-center space-x-1.5 ${
            isUser1
              ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
              : 'bg-emerald-50 text-emerald-800 border-emerald-200'
          }`}>
            <span className={`w-1.5 h-1.5 rounded-full ${isUser1 ? 'bg-indigo-600' : 'bg-emerald-600'}`} />
            <span>{isUser1 ? 'Demo Mode (Mock Data)' : 'Live Gmail Synced'}</span>
          </span>
        </div>

        {onRefresh && (
          <button
            onClick={() => {
              onRefresh();
              if (typeof window !== 'undefined') {
                window.dispatchEvent(new CustomEvent('refresh-dashboard-data'));
              }
            }}
            disabled={isRefreshing || isSwitching}
            title="Refresh Intelligence Data"
            className="p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-all"
          >
            <RotateCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-indigo-600' : ''}`} />
          </button>
        )}

        <div className="h-4 w-px bg-slate-200" />

        {/* User Identity Switcher Dropdown */}
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setIsDropdownOpen(!isDropdownOpen)}
            disabled={isSwitching}
            className="flex items-center space-x-2.5 p-1.5 rounded-xl hover:bg-slate-100 border border-transparent hover:border-slate-200 transition-all focus:outline-none"
            title="Switch Active User Profile (Stage 19B Multi-User)"
          >
            <div className={`w-8 h-8 rounded-full border flex items-center justify-center font-bold text-xs ${
              isUser1 
                ? 'bg-indigo-100 border-indigo-300 text-indigo-700' 
                : 'bg-emerald-100 border-emerald-300 text-emerald-800'
            }`}>
              {userInitials}
            </div>
            <div className="hidden sm:block text-left">
              <div className="flex items-center space-x-1.5">
                <p className="text-xs font-semibold text-slate-800 leading-tight">
                  {currentUser?.name || 'Loading User...'}
                </p>
                <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                  isUser1 ? 'bg-indigo-100 text-indigo-700' : 'bg-emerald-100 text-emerald-800'
                }`}>
                  {isUser1 ? 'Mock Demo Profile' : 'Connected Gmail'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 font-mono truncate max-w-[200px]">
                {currentUser?.email || 'Resolving identity...'}
              </p>
            </div>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
          </button>

          {/* Switcher Dropdown Menu */}
          {isDropdownOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-lg border border-slate-200 py-2 z-50 animate-in fade-in slide-in-from-top-2 duration-150">
              <div className="px-3.5 py-2 border-b border-slate-100">
                <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                  Account Switcher
                </p>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  Strict server-controlled session isolation
                </p>
              </div>

              <div className="p-1 space-y-1">
                {users.map((u) => {
                  const isSelected = currentUser?.id === u.id;
                  const isMock = u.id === 1;
                  return (
                    <button
                      key={u.id}
                      type="button"
                      onClick={() => handleSwitchUser(u.email)}
                      className={`w-full text-left px-3 py-2.5 rounded-lg text-xs transition-colors flex items-start justify-between ${
                        isSelected 
                          ? 'bg-indigo-50/80 text-indigo-900 border border-indigo-200/80' 
                          : 'hover:bg-slate-50 text-slate-700'
                      }`}
                    >
                      <div className="space-y-0.5 pr-2">
                        <div className="flex items-center space-x-1.5">
                          <span className={`font-semibold ${isSelected ? 'text-indigo-900' : 'text-slate-800'}`}>
                            {u.name}
                          </span>
                          <span className={`text-[10px] font-semibold px-1.5 py-0.2 rounded ${
                            isMock ? 'bg-indigo-100 text-indigo-700' : 'bg-emerald-100 text-emerald-800'
                          }`}>
                            {isMock ? 'Mock Provider' : 'Gmail'}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 font-mono truncate">{u.email}</p>
                        <p className="text-[10px] text-slate-400">{u.role}</p>
                      </div>
                      {isSelected && (
                        <Check className="w-4 h-4 text-indigo-600 mt-1 flex-shrink-0" />
                      )}
                    </button>
                  );
                })}
              </div>

              <div className="p-1 border-t border-slate-100">
                <button
                  type="button"
                  onClick={handleConnectAnotherAccount}
                  className="w-full text-left px-3 py-2 rounded-lg text-xs font-semibold text-indigo-600 hover:bg-indigo-50 flex items-center space-x-2 transition-colors"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Connect another Gmail account</span>
                </button>
              </div>

              <div className="px-3.5 py-2 border-t border-slate-100 bg-slate-50/60 rounded-b-xl">
                <div className="flex items-center space-x-1 text-[11px] text-slate-500">
                  <Shield className="w-3 h-3 text-emerald-600 flex-shrink-0" />
                  <span>Data isolation enforced server-side. Zero credential bleed.</span>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
};
