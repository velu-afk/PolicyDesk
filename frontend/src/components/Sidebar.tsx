import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  ShieldCheck,
  LayoutDashboard,
  MessageSquareText,
  History,
  FileText,
  Users,
  Activity,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

export const Sidebar: React.FC = () => {
  const { user } = useAuth();
  const isAdmin = user?.role === 'admin';

  const navItemClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all ${
      isActive
        ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-950/30'
        : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
    }`;

  return (
    <aside className="w-64 bg-slate-900 text-slate-100 flex flex-col border-r border-slate-800 shrink-0">
      {/* Brand Header */}
      <div className="h-16 px-5 flex items-center gap-3 border-b border-slate-800">
        <div className="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center shadow-inner">
          <ShieldCheck className="w-5 h-5 text-white" />
        </div>
        <div>
          <span className="font-bold text-base tracking-tight text-white block leading-none">
            PolicyDesk
          </span>
          <span className="text-[11px] font-medium text-indigo-400 tracking-wide uppercase mt-1 block">
            Enterprise RAG AI
          </span>
        </div>
      </div>

      {/* Navigation Links */}
      <div className="flex-1 overflow-y-auto py-5 px-3 space-y-6">
        {isAdmin && (
          <div>
            <p className="px-3.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Administration
            </p>
            <nav className="space-y-1">
              <NavLink to="/admin" end className={navItemClass}>
                <Activity className="w-4 h-4" />
                <span>Admin Overview</span>
              </NavLink>
              <NavLink to="/admin/documents" className={navItemClass}>
                <FileText className="w-4 h-4" />
                <span>Document Management</span>
              </NavLink>
              <NavLink to="/admin/users" className={navItemClass}>
                <Users className="w-4 h-4" />
                <span>User Management</span>
              </NavLink>
            </nav>
          </div>
        )}

        <div>
          <p className="px-3.5 text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
            Knowledge Workspace
          </p>
          <nav className="space-y-1">
            <NavLink to="/dashboard" className={navItemClass}>
              <LayoutDashboard className="w-4 h-4" />
              <span>User Dashboard</span>
            </NavLink>
            <NavLink to="/chat" className={navItemClass}>
              <MessageSquareText className="w-4 h-4" />
              <span>AI Policy Assistant</span>
            </NavLink>
            <NavLink to="/history" className={navItemClass}>
              <History className="w-4 h-4" />
              <span>Conversation History</span>
            </NavLink>
          </nav>
        </div>
      </div>

      {/* Grounding Status Footer */}
      <div className="p-4 m-3 rounded-xl bg-slate-800/70 border border-slate-700/70">
        <div className="flex items-center gap-2 text-xs font-semibold text-emerald-400">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span>Strict Source Grounding</span>
        </div>
        <p className="text-[11px] text-slate-400 mt-1 leading-relaxed">
          Answers are generated exclusively from verified policy chunks with pgvector cosine search.
        </p>
      </div>
    </aside>
  );
};
