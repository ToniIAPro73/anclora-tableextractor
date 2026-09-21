import "@/App.css";
import React from "react";
import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { LangProvider } from "@/contexts/LangContext";
import { AuthProvider, useAuth } from "@/contexts/AuthContext";
import { AuthCallback } from "@/components/AuthCallback";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import Login from "@/pages/Login";
import Upload from "@/pages/Upload";
import Review from "@/pages/Review";
import History from "@/pages/History";
import { Table2 } from "lucide-react";

const RootRoute = () => {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/30 animate-pulse">
          <Table2 className="h-7 w-7 text-primary" />
        </div>
      </div>
    );
  }
  return user ? <Navigate to="/upload" replace /> : <Login />;
};

function AppRouter() {
  const location = useLocation();
  // Handle Emergent OAuth callback synchronously (read reactive hash, not window.location.hash)
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/" element={<RootRoute />} />
      <Route path="/upload" element={<ProtectedRoute><Upload /></ProtectedRoute>} />
      <Route path="/review" element={<ProtectedRoute><Review /></ProtectedRoute>} />
      <Route path="/review/:docId" element={<ProtectedRoute><Review /></ProtectedRoute>} />
      <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <ThemeProvider>
      <LangProvider>
        <BrowserRouter>
          <AuthProvider>
            <div className="App">
              <AppRouter />
              <Toaster position="top-right" richColors closeButton />
            </div>
          </AuthProvider>
        </BrowserRouter>
      </LangProvider>
    </ThemeProvider>
  );
}

export default App;
