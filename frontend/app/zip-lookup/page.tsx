import { Suspense } from "react";
import { ZipLookupClient } from "@/components/ZipLookupClient";

export default function ZipLookupPage() {
  return (
    <Suspense fallback={<div className="text-sm text-slate-400">Loading lookup…</div>}>
      <ZipLookupClient />
    </Suspense>
  );
}
