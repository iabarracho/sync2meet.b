"use client";



import { usePathname } from "next/navigation";

import { Sidebar } from "@/components/layout/sidebar";

import { ApiStatusBanner } from "@/components/layout/api-status";



export function AppShell({ children }: { children: React.ReactNode }) {

  const pathname = usePathname();

  const isLogin =

    pathname.startsWith("/login") || pathname.startsWith("/register");



  if (isLogin) {

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

