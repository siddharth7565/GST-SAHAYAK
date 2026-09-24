import React, { useState, useEffect } from 'react';
import { AppShell } from './components/layout/AppShell';
import { NavItemKey } from './components/layout/Sidebar';
import { checkHealth } from './api';
import { Dashboard } from './pages/Dashboard';
import { SingleLLM } from './pages/SingleLLM';
import { MultiLLM } from './pages/MultiLLM';
import { HistoryPage } from './pages/History';
import { SavedQueriesPage } from './pages/SavedQueries';

export default function App() {
  const [activeNav, setActiveNav] = useState<NavItemKey>('dashboard');
  const [healthStatus, setHealthStatus] = useState<'checking' | 'connected' | 'disconnected'>('checking');

  // Session search params passed between views
  const [activeQuery, setActiveQuery] = useState('');
  const [activeFY, setActiveFY] = useState('');
  const [activeAsOfDate, setActiveAsOfDate] = useState('');

  // Check health on mount
  useEffect(() => {
    handleCheckHealth();
  }, []);

  const handleCheckHealth = async () => {
    setHealthStatus('checking');
    try {
      const data = await checkHealth();
      if (data.status === 'ok') {
        setHealthStatus('connected');
      } else {
        setHealthStatus('disconnected');
      }
    } catch {
      setHealthStatus('disconnected');
    }
  };

  // + New Research button handler: resets current query & filters and navigates to Single LLM page
  const handleNewResearch = () => {
    setActiveQuery('');
    setActiveFY('');
    setActiveAsOfDate('');
    setActiveNav('single');
  };

  // Open existing query from History or Saved Queries
  const handleOpenQuery = (query: string, mode: 'single' | 'multi', fy: string = '', asOfDate: string = '') => {
    setActiveQuery(query);
    setActiveFY(fy);
    setActiveAsOfDate(asOfDate);
    setActiveNav(mode);
  };

  // Run search from Dashboard
  const handleRunDashboardSearch = (query: string, mode: 'single' | 'multi', fy: string, asOfDate: string) => {
    setActiveQuery(query);
    setActiveFY(fy);
    setActiveAsOfDate(asOfDate);
    setActiveNav(mode);
  };

  return (
    <AppShell
      activeNav={activeNav}
      onNavigate={(nav) => {
        // Reset state when switching unless explicitly navigating with query
        setActiveNav(nav);
      }}
      onNewResearch={handleNewResearch}
      healthStatus={healthStatus}
      onCheckHealth={handleCheckHealth}
    >
      {activeNav === 'dashboard' && (
        <Dashboard
          onNavigate={(nav, query) => {
            if (query) setActiveQuery(query);
            setActiveNav(nav);
          }}
          onRunSearch={handleRunDashboardSearch}
        />
      )}

      {activeNav === 'single' && (
        <SingleLLM
          key={`single_${activeQuery}_${activeFY}`}
          initialQuery={activeQuery}
          initialFY={activeFY}
          initialAsOfDate={activeAsOfDate}
        />
      )}

      {activeNav === 'multi' && (
        <MultiLLM
          key={`multi_${activeQuery}_${activeFY}`}
          initialQuery={activeQuery}
          initialFY={activeFY}
          initialAsOfDate={activeAsOfDate}
        />
      )}

      {activeNav === 'history' && (
        <HistoryPage onOpenQuery={handleOpenQuery} />
      )}

      {activeNav === 'saved' && (
        <SavedQueriesPage onOpenQuery={handleOpenQuery} />
      )}
    </AppShell>
  );
}
