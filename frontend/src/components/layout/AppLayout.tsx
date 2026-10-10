import React, { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';
import { Header } from './Header';
import { api } from '../../services/api';
import { DashboardMetrics } from '../../types';

export const AppLayout: React.FC = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchMetrics = async () => {
    try {
      setIsRefreshing(true);
      const data = await api.getDashboard();
      setMetrics(data.metrics);
    } catch (err) {
      console.error('Failed to fetch dashboard metrics:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  return (
    <div className="flex h-screen bg-slate-50 overflow-hidden font-sans text-slate-800">
      {/* Fixed Left Sidebar */}
      <Sidebar metrics={metrics} />

      {/* Main Content Pane */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header onRefresh={fetchMetrics} isRefreshing={isRefreshing} />

        {/* Scrollable Page Outlet */}
        <main className="flex-1 overflow-y-auto bg-slate-50 p-6 md:p-8">
          <div className="max-w-7xl mx-auto">
            <Outlet context={{ metrics, refreshMetrics: fetchMetrics }} />
          </div>
        </main>
      </div>
    </div>
  );
};
