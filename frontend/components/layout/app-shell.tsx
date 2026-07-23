"use client";



import { usePathname } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";

import { ApiStatusBanner } from "@/components/layout/api-status";



export function AppShell({ children }: { children: React.ReactNode }) {

  const pathname = usePathname();

  const isAuthPage =
    pathname.startsWith("/login") ||
    pathname.startsWith("/register") ||
    pathname.startsWith("/forgot-password") ||
    pathname.startsWith("/reset-password");

  if (isAuthPage) {

    return <>{children}</>;

  }



  return (

    <div className="flex min-h-screen">

      <Sidebar />

      <main className="flex-1 overflow-auto">

        <ApiStatusBanner />

        {children}

      </main>

    </div>

  );

}

