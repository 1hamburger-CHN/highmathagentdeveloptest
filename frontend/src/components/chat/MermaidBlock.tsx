"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  code: string;
}

/** Wrap Mermaid node labels containing special characters in quotes so the parser doesn't choke. */
function sanitizeMermaid(input: string): string {
  // Fix unquoted square-bracket labels like A[lim(x→0) sinx/x = 1]
  // Replace [...] with ["..."] if the content has special chars and isn't already quoted
  return input.replace(/\[([^\]]+)\]/g, (_, label: string) => {
    // Already quoted with double or single quotes — leave as-is
    if (/^["'].*["']$/.test(label.trim())) return `[${label}]`;
    // Contains special characters that break Mermaid parsing
    if (/[(){}<>→εδαβγλθ∞πσΣΩ≈≠≤≥±×÷√∫∮∂∇∏∑←↑↓↔⇒⇔∀∃¬∧∨∩∪⊂⊃∈∉∥⊥∠△◻]/.test(label)) {
      return `["${label.replace(/"/g, '\\"')}"]`;
    }
    return `[${label}]`;
  });
}

export default function MermaidBlock({ code }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const idRef = useRef(`mermaid-${Math.random().toString(36).slice(2, 9)}`);

  useEffect(() => {
    let cancelled = false;
    const renderDiagram = async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });
        const sanitized = sanitizeMermaid(code);
        const { svg } = await mermaid.render(idRef.current, sanitized);
        if (!cancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (e) {
        if (!cancelled) {
          setError("Mermaid 渲染异常");
          console.error("Mermaid render error:", e);
        }
      }
    };
    renderDiagram();
    return () => { cancelled = true; };
  }, [code]);

  if (error) {
    return (
      <div className="my-2 p-3 bg-red-50 rounded-lg border border-red-200">
        <p className="text-xs text-red-600 mb-2">{error}</p>
        <pre className="text-xs text-gray-600 overflow-x-auto">{code}</pre>
      </div>
    );
  }

  return (
    <div className="my-2 p-3 bg-white rounded-lg border border-gray-200 overflow-x-auto">
      <div ref={containerRef} className="flex justify-center" />
    </div>
  );
}
