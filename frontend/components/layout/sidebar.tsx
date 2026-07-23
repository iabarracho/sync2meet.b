"use client";

import Image from "next/image";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Calendar,
  FileText,
  LayoutDashboard,
  Layers,
  LogOut,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { APP_NAME, APP_TAGLINE } from "@/lib/branding";
import { api } from "@/lib/api";
import { authEnabled, clearToken } from "@/lib/auth";
import { Button } from "@/components/ui/button";

const links = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/meetings", label: "Reuniões", icon: Calendar },
  { href: "/templates", label: "Templates", icon: FileText },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [userName, setUserName] = useState<string | null>(null);

  useEffect(() => {
    if (!authEnabled()) return;
    api.auth
      .me()
      .then((user) => setUserName(user.name))
      .catch(() => setUserName(null));
  }, []);

  async function logout() {
    try {
      await api.auth.logout();
    } catch {
      /* ignore */
    }
    clearToken();
    router.push("/login");
    router.refresh();
  }

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-slate-200 bg-slate-950 text-white">
      <div className="flex items-center gap-3 border-b border-slate-800 px-5 py-5">
        <Image
          src="/logo-bocaboca.png"
          alt="BocàBoca"
          width={36}
          height={36}
          className="rounded-lg"
        />
        <div className="min-w-0">
          <p className="truncate font-semibold tracking-tight">{APP_NAME}</p>
          <p className="truncate text-xs text-slate-400">{APP_TAGLINE}</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 p-4">
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
              pathname === href || (href !== "/" && pathname.startsWith(href))
                ? "bg-brand-600 text-white"
                : "text-slate-300 hover:bg-slate-800 hover:text-white"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>
      <div className="border-t border-slate-800 p-4 text-xs text-slate-500">
        <div className="mb-3 flex items-center gap-2">
          <Layers className="h-3 w-3" />
          Agenda → Ata → Distribuição
        </div>
        {authEnabled() && userName ? (
          <div className="space-y-2">
            <p className="text-slate-400">Sessão: {userName}</p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="w-full border-slate-700 bg-transparent text-slate-300 hover:bg-slate-800"
              onClick={() => void logout()}
            >
              <LogOut className="h-3 w-3" />
              Sair
            </Button>
          </div>
        ) : null}
      </div>
    </aside>
  );
}
