import React from 'react';
import {
  Plus,
  LayoutDashboard,
  Sparkles,
  ShieldCheck,
  History,
  Bookmark,
  Scale,
  Activity,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { Button } from '../ui/button';

export type NavItemKey = 'dashboard' | 'single' | 'multi' | 'history' | 'saved';

interface SidebarProps {
  activeNav: NavItemKey;
  onNavigate: (nav: NavItemKey) => void;
  onNewResearch: () => void;
  healthStatus: 'checking' | 'connected' | 'disconnected';
}

export function Sidebar({ activeNav, onNavigate, onNewResearch, healthStatus }: SidebarProps) {
  return (
    <aside className="w-64 bg-white border-r border-gst-border flex flex-col h-screen sticky top-0 z-30 shadow-xs select-none">
      {/* Brand Header */}
      <div className="p-5 border-b border-gst-border/50 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gst-orange/20 border border-gst-orange/40 flex items-center justify-center text-gst-orange-deep shadow-xs">
            <Scale className="h-5 w-5 stroke-[2.2]" />
          </div>
          <div>
            <div className="font-extrabold text-base tracking-tight leading-none text-gst-dark flex items-center gap-1.5">
              GST <span className="text-gst-orange-deep font-black">SAHAYAK</span>
            </div>
            <div className="text-[10px] uppercase tracking-wider font-semibold text-gst-muted mt-1">
              Legal Research Platform
            </div>
          </div>
        </div>
      </div>

      {/* Action Button: + New Research */}
      <div className="p-4">
        <Button
          onClick={onNewResearch}
          className="w-full justify-center gap-2 bg-gst-orange hover:bg-gst-orange-hover text-gst-dark font-semibold shadow-gst-subtle h-10 transition-all hover:scale-[1.01]"
        >
          <Plus className="h-4 w-4 stroke-[2.5]" />
          <span>New Research</span>
        </Button>
      </div>

      {/* Navigation Sections */}
      <nav className="flex-1 px-3 py-2 space-y-6 overflow-y-auto">
        {/* Main Nav */}
        <div>
          <button
            onClick={() => onNavigate('dashboard')}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
              activeNav === 'dashboard'
                ? "bg-gst-orange-verylight text-gst-orange-deep font-semibold border-l-4 border-gst-orange pl-2"
                : "text-gst-dark hover:bg-gst-orange-verylight/60 hover:text-gst-orange-deep"
            )}
          >
            <LayoutDashboard className={cn("h-4 w-4", activeNav === 'dashboard' ? "text-gst-orange-deep" : "text-gst-muted")} />
            <span>Dashboard</span>
          </button>
        </div>

        {/* Research Group */}
        <div className="space-y-1">
          <div className="px-3 text-[10px] font-bold uppercase tracking-wider text-gst-muted mb-1">
            Research Workspaces
          </div>
          <button
            onClick={() => onNavigate('single')}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
              activeNav === 'single'
                ? "bg-gst-orange-verylight text-gst-orange-deep font-semibold border-l-4 border-gst-orange pl-2"
                : "text-gst-dark hover:bg-gst-orange-verylight/60 hover:text-gst-orange-deep"
            )}
          >
            <Sparkles className={cn("h-4 w-4", activeNav === 'single' ? "text-gst-orange-deep" : "text-gst-muted")} />
            <span>Single LLM</span>
          </button>
          <button
            onClick={() => onNavigate('multi')}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
              activeNav === 'multi'
                ? "bg-gst-orange-verylight text-gst-orange-deep font-semibold border-l-4 border-gst-orange pl-2"
                : "text-gst-dark hover:bg-gst-orange-verylight/60 hover:text-gst-orange-deep"
            )}
          >
            <ShieldCheck className={cn("h-4 w-4", activeNav === 'multi' ? "text-gst-orange-deep" : "text-gst-muted")} />
            <span>Multi LLM Verification</span>
          </button>
        </div>

        {/* Library Group */}
        <div className="space-y-1">
          <div className="px-3 text-[10px] font-bold uppercase tracking-wider text-gst-muted mb-1">
            Research Library
          </div>
          <button
            onClick={() => onNavigate('history')}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
              activeNav === 'history'
                ? "bg-gst-orange-verylight text-gst-orange-deep font-semibold border-l-4 border-gst-orange pl-2"
                : "text-gst-dark hover:bg-gst-orange-verylight/60 hover:text-gst-orange-deep"
            )}
          >
            <History className={cn("h-4 w-4", activeNav === 'history' ? "text-gst-orange-deep" : "text-gst-muted")} />
            <span>Query History</span>
          </button>
          <button
            onClick={() => onNavigate('saved')}
            className={cn(
              "w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all",
              activeNav === 'saved'
                ? "bg-gst-orange-verylight text-gst-orange-deep font-semibold border-l-4 border-gst-orange pl-2"
                : "text-gst-dark hover:bg-gst-orange-verylight/60 hover:text-gst-orange-deep"
            )}
          >
            <Bookmark className={cn("h-4 w-4", activeNav === 'saved' ? "text-gst-orange-deep" : "text-gst-muted")} />
            <span>Saved Queries</span>
          </button>
        </div>
      </nav>

      {/* Bottom Status Card */}
      <div className="p-4 border-t border-gst-border/50 bg-gst-cream/30">
        <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg border border-gst-border/40 bg-white shadow-2xs">
          <span className="relative flex h-2.5 w-2.5">
            {healthStatus === 'connected' ? (
              <>
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-gst-green opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-gst-green"></span>
              </>
            ) : healthStatus === 'checking' ? (
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-400 animate-pulse"></span>
            ) : (
              <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-gst-red"></span>
            )}
          </span>
          <div className="flex-1 min-w-0">
            <div className="text-xs font-semibold text-gst-dark truncate">
              {healthStatus === 'connected' && 'System Operational'}
              {healthStatus === 'checking' && 'Connecting...'}
              {healthStatus === 'disconnected' && 'Backend Offline'}
            </div>
            <div className="text-[10px] text-gst-muted truncate">FastAPI + pgvector RAG</div>
          </div>
          <Activity className="h-3.5 w-3.5 text-gst-muted shrink-0" />
        </div>
      </div>
    </aside>
  );
}
