import React from 'react';
import { NavItemKey } from './Sidebar';
import { Badge } from '../ui/badge';
import { User, RefreshCw, Menu } from 'lucide-react';
import { Button } from '../ui/button';

interface TopBarProps {
  activeNav: NavItemKey;
  healthStatus: 'checking' | 'connected' | 'disconnected';
  onCheckHealth: () => void;
  onOpenMobileMenu?: () => void;
}

const SECTION_TITLES: Record<NavItemKey, { title: string; subtitle: string }> = {
  dashboard: {
    title: 'Research Dashboard',
    subtitle: 'Overview & recent GST legal queries',
  },
  single: {
    title: 'SINGLE LLM',
    subtitle: 'Direct GST research using the configured AI model',
  },
  multi: {
    title: 'MULTI LLM',
    subtitle: 'Compare multiple AI models against identical GST evidence',
  },
  history: {
    title: 'Query History',
    subtitle: 'Audit log of past legal research sessions',
  },
  saved: {
    title: 'Saved Queries',
    subtitle: 'Bookmarked GST questions for rapid reference',
  },
};

export function TopBar({ activeNav, healthStatus, onCheckHealth, onOpenMobileMenu }: TopBarProps) {
  const currentInfo = SECTION_TITLES[activeNav] || { title: 'GST Sahayak', subtitle: 'Legal Research Assistant' };

  return (
    <header className="h-16 bg-white/80 backdrop-blur-md border-b border-gst-border px-6 flex items-center justify-between sticky top-0 z-20 shadow-2xs">
      {/* Left: Mobile Menu Toggle & Title */}
      <div className="flex items-center gap-3">
        {onOpenMobileMenu && (
          <button
            onClick={onOpenMobileMenu}
            className="md:hidden p-2 rounded-lg text-gst-dark hover:bg-gst-orange-light/50"
            aria-label="Open navigation menu"
          >
            <Menu className="h-5 w-5" />
          </button>
        )}

        <div>
          <h1 className="text-lg font-extrabold tracking-tight text-gst-dark flex items-center gap-2">
            {currentInfo.title}
          </h1>
          <p className="text-xs text-gst-muted font-normal hidden sm:block">
            {currentInfo.subtitle}
          </p>
        </div>
      </div>

      {/* Right: Controls & Avatar */}
      <div className="flex items-center gap-3">
        {/* Backend status indicator */}
        <button
          onClick={onCheckHealth}
          className="flex items-center gap-2 px-3 py-1.5 rounded-full border border-gst-border bg-gst-cream/60 hover:bg-gst-orange-verylight text-xs transition-colors cursor-pointer"
          title="Click to re-check backend connection"
        >
          <span className="relative flex h-2 w-2">
            {healthStatus === 'connected' ? (
              <span className="relative inline-flex rounded-full h-2 w-2 bg-gst-green"></span>
            ) : healthStatus === 'checking' ? (
              <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500 animate-pulse"></span>
            ) : (
              <span className="relative inline-flex rounded-full h-2 w-2 bg-gst-red"></span>
            )}
          </span>
          <span className="font-semibold text-gst-dark hidden sm:inline">
            {healthStatus === 'connected' && 'API Connected'}
            {healthStatus === 'checking' && 'Checking...'}
            {healthStatus === 'disconnected' && 'Disconnected'}
          </span>
          <RefreshCw className="h-3 w-3 text-gst-muted hover:rotate-180 transition-transform duration-300" />
        </button>

        {/* Version Badge */}
        <Badge variant="outline" className="hidden sm:inline-flex text-[11px] font-mono border-gst-border/80 text-gst-muted">
          v1.0
        </Badge>

        {/* Practitioner Avatar */}
        <div className="flex items-center gap-2 pl-2 border-l border-gst-border/60">
          <div className="h-8 w-8 rounded-full bg-gst-orange-light border border-gst-orange/40 flex items-center justify-center text-gst-orange-deep font-semibold text-xs shadow-2xs">
            <User className="h-4 w-4" />
          </div>
          <div className="hidden lg:block text-left">
            <div className="text-xs font-bold leading-none text-gst-dark">Tax Practitioner</div>
            <div className="text-[10px] text-gst-muted leading-tight">CA / Legal Expert</div>
          </div>
        </div>
      </div>
    </header>
  );
}
