import { Suspense } from "react";
import ResetPasswordForm from "./reset-password-form";

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="p-8 text-center">A carregar…</div>}>
      <ResetPasswordForm />
    </Suspense>
  );
}
