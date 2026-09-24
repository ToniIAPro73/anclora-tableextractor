import React from "react";
import { NavLink, useNavigate } from "react-router-dom";
import { Upload, FileSpreadsheet, History, LogOut } from "lucide-react";
import { BrandMark } from "@/components/BrandMark";
import { ThemeToggle } from "@/components/ThemeToggle";
import { LangToggle } from "@/components/LangToggle";
import { useLang } from "@/contexts/LangContext";
import { useAuth } from "@/contexts/AuthContext";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

export const Header = () => {
  const { t } = useLang();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const links = [
    { to: "/upload", label: t("nav.upload"), icon: Upload, testid: "nav-upload" },
    { to: "/review", label: t("nav.review"), icon: FileSpreadsheet, testid: "nav-review" },
    { to: "/history", label: t("nav.history"), icon: History, testid: "nav-history" },
  ];

  return (
    <header
      data-testid="app-header"
      className="sticky top-0 z-50 border-b border-border bg-background/80 backdrop-blur-xl"
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo */}
        <button
          data-testid="logo-home"
          aria-label={t("common.appName")}
          onClick={() => navigate("/upload")}
          className="flex items-center gap-2.5 group"
        >
          <span className="relative flex h-9 w-9 items-center justify-center overflow-hidden rounded-full ring-1 ring-primary/30">
            <BrandMark className="h-full w-full" />
          </span>
          <span className="hidden flex-col items-start leading-none sm:flex">
            <span className="text-[15px] font-bold tracking-tight" style={{ fontFamily: "Manrope, Inter, sans-serif" }}>
              Anclora <span className="text-primary">TableExtract</span>
            </span>
          </span>
        </button>

        {/* Center nav */}
        <nav className="hidden items-center gap-1 md:flex">
          {links.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                data-testid={link.testid}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted"
                  }`
                }
              >
                <Icon className="h-4 w-4" strokeWidth={1.7} />
                {link.label}
              </NavLink>
            );
          })}
        </nav>

        {/* Right controls */}
        <div className="flex items-center gap-2.5">
          <LangToggle />
          <ThemeToggle />
          {user && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button data-testid="user-menu-button" className="ml-1 rounded-full ring-1 ring-border hover:ring-primary/50 transition">
                  <Avatar className="h-9 w-9">
                    <AvatarImage src={user.picture} alt={user.name} />
                    <AvatarFallback className="bg-primary/15 text-primary text-sm font-semibold">
                      {(user.name || user.email || "?").slice(0, 1).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="min-w-[13rem]">
                <DropdownMenuLabel className="flex flex-col">
                  <span className="text-sm font-semibold">{user.name}</span>
                  <span className="text-xs text-muted-foreground truncate">{user.email}</span>
                </DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem data-testid="logout-button" onClick={logout} className="gap-2 cursor-pointer text-destructive">
                  <LogOut className="h-4 w-4" /> {t("nav.logout")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
      </div>

      {/* Mobile nav */}
      <nav className="flex items-center gap-1 overflow-x-auto border-t border-border px-3 py-2 md:hidden thin-scroll">
        {links.map((link) => {
          const Icon = link.icon;
          return (
            <NavLink
              key={link.to}
              to={link.to}
              data-testid={`${link.testid}-mobile`}
              className={({ isActive }) =>
                `flex items-center gap-1.5 whitespace-nowrap rounded-full px-3 py-1.5 text-sm font-medium ${
                  isActive ? "bg-primary/10 text-primary" : "text-muted-foreground"
                }`
              }
            >
              <Icon className="h-4 w-4" strokeWidth={1.7} />
              {link.label}
            </NavLink>
          );
        })}
      </nav>
    </header>
  );
};
