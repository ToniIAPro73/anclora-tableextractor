import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import { BrandMark } from "@/components/BrandMark";

export const ProtectedRoute = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/30 animate-pulse">
          <BrandMark className="h-14 w-14" />
        </div>
      </div>
    );
  }

  if (!user) return <Navigate to="/" replace />;
  return children;
};
