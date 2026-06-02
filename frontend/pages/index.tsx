import React, { useState, useEffect } from "react";
import Head from "next/head";
import { Sidebar } from "../components/Sidebar";
import { ChatInterface } from "../components/ChatInterface";
import { DocumentManager } from "../components/DocumentManager";
import { AnalyticsDashboard } from "../components/AnalyticsDashboard";
import { apiService, DocumentResponse, AnalyticsResponse } from "../services/api";

export default function Home() {
  const [activeTab, setActiveTab] = useState("chat");
  const [systemStatus, setSystemStatus] = useState("checking");
  
  const [documents, setDocuments] = useState<DocumentResponse[]>([]);
  const [analytics, setAnalytics] = useState<AnalyticsResponse | null>(null);
  const [analyticsLoading, setAnalyticsLoading] = useState(false);

  // Synchronize document lists
  const fetchDocuments = async () => {
    try {
      const data = await apiService.listDocuments();
      setDocuments(data);
      setSystemStatus("online");
    } catch (err) {
      console.error("Failed to fetch documents:", err);
      setSystemStatus("offline");
    }
  };

  // Synchronize analytics metrics
  const fetchAnalytics = async () => {
    setAnalyticsLoading(true);
    try {
      const data = await apiService.getAnalytics();
      setAnalytics(data);
    } catch (err) {
      console.error("Failed to fetch analytics metrics:", err);
    } finally {
      setAnalyticsLoading(false);
    }
  };

  // Perform initial synchronization
  useEffect(() => {
    fetchDocuments();
  }, []);

  // Fetch contextual details when switching tabs
  useEffect(() => {
    if (activeTab === "documents") {
      fetchDocuments();
    } else if (activeTab === "analytics") {
      fetchAnalytics();
    }
  }, [activeTab]);

  return (
    <div className="flex h-screen bg-slate-dark font-sans antialiased text-slate-200 overflow-hidden">
      <Head>
        <title>Enterprise Knowledge Intelligence Platform - Next-Gen RAG System</title>
        <meta name="description" content="Production-ready high-precision hybrid retrieval and advanced document reasoning synthesis." />
        <link rel="icon" href="/favicon.ico" />
        {/*Outfit Google font */}
        <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
      </Head>

      {/* Navigation sidebar menu */}
      <Sidebar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        systemStatus={systemStatus}
      />

      {/* Main viewport panels */}
      <main className="flex-1 h-full overflow-hidden bg-slate-950">
        {activeTab === "chat" && (
          <ChatInterface documents={documents} />
        )}
        
        {activeTab === "documents" && (
          <DocumentManager
            documents={documents}
            onRefresh={fetchDocuments}
          />
        )}
        
        {activeTab === "analytics" && (
          <AnalyticsDashboard
            analytics={analytics}
            loading={analyticsLoading}
          />
        )}
      </main>
    </div>
  );
}
