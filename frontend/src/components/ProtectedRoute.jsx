import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { Table2 } from "lucide-react";

export const ProtectedRoute = ({ children }) => {
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

  if (!user) return <Navigate to="/" replace />;
  return children;
};
