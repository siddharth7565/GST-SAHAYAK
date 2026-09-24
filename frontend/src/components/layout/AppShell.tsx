import React, { useState } from 'react';
import { Sidebar, NavItemKey } from './Sidebar';
import { TopBar } from './TopBar';

interface AppShellProps {
  activeNav: NavItemKey;
  onNavigate: (nav: NavItemKey) => void;
  onNewResearch: () => void;
  healthStatus: 'checking' | 'connected' | 'disconnected';
  onCheckHealth: () => void;
  children: React.ReactNode;
}

export function AppShell({
  activeNav,
  onNavigate,
  onNewResearch,
  healthStatus,
  onCheckHealth,
  children,
}: AppShellProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleMobileNav = (nav: NavItemKey) => {
    onNavigate(nav);
    setMobileMenuOpen(false);
  };

  const handleMobileNewResearch = () => {
    onNewResearch();
    setMobileMenuOpen(false);
  };

  return (
    <div className="min-h-screen bg-gst-cream text-gst-dark flex flex-col md:flex-row antialiased">
      {/* Desktop Sidebar */}
      <div className="hidden md:block shrink-0">
        <Sidebar
          activeNav={activeNav}
          onNavigate={onNavigate}
          onNewResearch={onNewResearch}
          healthStatus={healthStatus}
        />
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 md:hidden flex">
          <div
            className="fixed inset-0 bg-gst-dark/60 backdrop-blur-xs"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="relative z-50 w-64 max-w-xs bg-white h-full shadow-2xl animate-in slide-in-from-left duration-200">
            <Sidebar
              activeNav={activeNav}
              onNavigate={handleMobileNav}
              onNewResearch={handleMobileNewResearch}
              healthStatus={healthStatus}
            />
          </div>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar
          activeNav={activeNav}
          healthStatus={healthStatus}
          onCheckHealth={onCheckHealth}
          onOpenMobileMenu={() => setMobileMenuOpen(true)}
        />
        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-7xl w-full mx-auto">
          {children}
        </main>
      </div>
    </div>
  );
}
