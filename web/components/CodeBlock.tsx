"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

export default function CodeBlock({ code, label }: { code: string; label: string }) {
  const [copied, setCopied] = useState(false);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      /* clipboard unavailable; the code stays selectable */
    }
  };
  return (
    <div className="relative rounded-xl border border-border bg-panel">
      <button
        type="button"
        onClick={copy}
        aria-label={copied ? "Copied" : `Copy ${label}`}
        className="absolute right-3 top-3 inline-flex items-center gap-1.5 rounded-md border border-border bg-bg px-2.5 py-1 text-[13px] text-ink"
      >
        {copied ? <Check size={14} aria-hidden /> : <Copy size={14} aria-hidden />}
        {copied ? "Copied" : "Copy"}
      </button>
      <pre className="overflow-x-auto p-5 pr-24 font-mono text-[14px] leading-relaxed text-ink">
        <code>{code}</code>
      </pre>
    </div>
  );
}
