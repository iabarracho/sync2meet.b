import Image from "next/image";
import { APP_NAME, APP_TAGLINE } from "@/lib/branding";

export function AuthShell({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden bg-neutral-50 px-4 py-10">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,_rgba(0,0,0,0.06),_transparent_55%)]"
      />
      <div className="relative w-full max-w-md">
        <div className="mb-8 flex flex-col items-center text-center">
          <Image
            src="/logo-bocaboca.png"
            alt="BocàBoca"
            width={72}
            height={72}
            className="mb-4 rounded-2xl shadow-sm"
            priority
            unoptimized
          />
          <p className="text-lg font-semibold tracking-tight text-neutral-900">
            {APP_NAME}
          </p>
          <p className="mt-1 text-sm text-neutral-500">{APP_TAGLINE}</p>
        </div>
        <div className="rounded-2xl border border-neutral-200/80 bg-white p-6 shadow-[0_20px_50px_-28px_rgba(0,0,0,0.35)] sm:p-8">
          <div className="mb-6">
            <h1 className="text-xl font-semibold tracking-tight text-neutral-900">
              {title}
            </h1>
            {subtitle ? (
              <p className="mt-1.5 text-sm leading-relaxed text-neutral-500">
                {subtitle}
              </p>
            ) : null}
          </div>
          {children}
        </div>
      </div>
    </div>
  );
}
