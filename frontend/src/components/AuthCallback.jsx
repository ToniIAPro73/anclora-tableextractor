import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { Table2 } from "lucide-react";

export const AuthCallback = () => {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = window.location.hash || "";
    const match = hash.match(/session_id=([^&]+)/);
    const sessionId = match ? decodeURIComponent(match[1]) : null;

    const run = async () => {
      if (!sessionId) {
        navigate("/");
        return;
      }
      try {
        const res = await api.post("/auth/session", { session_id: sessionId });
        setUser(res.data);
        window.history.replaceState(null, "", "/upload");
        navigate("/upload", { state: { user: res.data } });
      } catch (e) {
        navigate("/");
      }
    };
    run();
  }, [navigate, setUser]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background">
      <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 ring-1 ring-primary/30 animate-pulse">
        <Table2 className="h-7 w-7 text-primary" />
      </div>
      <p className="text-sm text-muted-foreground">Anclora TableExtract…</p>
    </div>
  );
};
