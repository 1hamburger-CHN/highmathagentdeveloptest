"use client";

import { useEffect, useRef, useState } from "react";

interface Props {
  code: string;
}

/** Quote all Mermaid node labels so special characters don't break the parser. */
function sanitizeMermaid(input: string): string {
  return input.replace(/\[([^\]]+?)\]/g, (_, label: string) => {
    // Already quoted — leave as-is
    const trimmed = label.trim();
    if ((trimmed.startsWith('"') && trimmed.endsWith('"')) ||
        (trimmed.startsWith("'") && trimmed.endsWith("'"))) {
      return `[${label}]`;
    }
    // Wrap in double quotes, escape existing double quotes
    return `["${label.replace(/"/g, '\\"')}"]`;
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
      } catch (e: any) {
        if (!cancelled) {
          const msg = e?.message || String(e);
          setError(`Mermaid 渲染异常: ${msg}`);
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
        <details className="text-xs text-gray-500">
          <summary className="cursor-pointer">原始代码</summary>
          <pre className="mt-1 text-xs text-gray-600 overflow-x-auto">{code}</pre>
        </details>
        <details className="text-xs text-gray-500">
          <summary className="cursor-pointer">处理后代码</summary>
          <pre className="mt-1 text-xs text-gray-600 overflow-x-auto">{sanitizeMermaid(code)}</pre>
        </details>
      </div>
    );
  }

  return (
    <div className="my-2 p-3 bg-white rounded-lg border border-gray-200 overflow-x-auto">
      <div ref={containerRef} className="flex justify-center" />
    </div>
  );
}
