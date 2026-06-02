import React from "react";

interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  systemStatus: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ activeTab, setActiveTab, systemStatus }) => {
  const menuItems = [
    {
      id: "chat",
      label: "Conversational RAG",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
      ),
    },
    {
      id: "documents",
      label: "Document Manager",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
    },
    {
      id: "analytics",
      label: "Admin Observability",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
        </svg>
      ),
    },
  ];

  return (
    <aside className="w-72 bg-slate-900 border-r border-slate-800 flex flex-col justify-between h-screen text-slate-200">
      <div className="p-6">
        {/* Brand Header */}
        <div className="flex items-center space-x-3 mb-8">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            </svg>
          </div>
          <div>
            <h1 className="font-bold text-lg bg-gradient-to-r from-white via-slate-200 to-indigo-300 bg-clip-text text-transparent leading-none">
              Enterprise Knowledge
            </h1>
            <span className="text-[10px] text-indigo-400 font-semibold tracking-wider uppercase">
              Intelligence Platform
            </span>
          </div>
        </div>

        {/* Menu Navigation */}
        <nav className="space-y-1.5">
          {menuItems.map((item) => {
            const active = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center space-x-3.5 px-4 py-3 rounded-xl transition-all duration-300 text-sm font-medium ${
                  active
                    ? "bg-gradient-to-r from-indigo-600/35 to-purple-600/15 border border-indigo-500/30 text-indigo-200 shadow-md shadow-indigo-500/5"
                    : "hover:bg-slate-800/50 text-slate-400 hover:text-slate-200 border border-transparent"
                }`}
              >
                <span className={active ? "text-indigo-400" : "text-slate-500"}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Footer System Status Banner */}
      <div className="p-6 border-t border-slate-800 bg-slate-950/40">
        <div className="flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2">
            <span className={`relative flex h-2 w-2`}>
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${systemStatus === "online" ? "bg-emerald-400" : "bg-amber-400"} opacity-75`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${systemStatus === "online" ? "bg-emerald-500" : "bg-amber-500"}`}></span>
            </span>
            <span className="text-slate-400 font-medium">Core Service Status</span>
          </div>
          <span className={`font-semibold capitalize ${systemStatus === "online" ? "text-emerald-400" : "text-amber-400"}`}>
            {systemStatus}
          </span>
        </div>
      </div>
    </aside>
  );
};
