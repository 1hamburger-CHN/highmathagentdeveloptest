"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { ZoomIn, ZoomOut, RotateCcw } from "lucide-react";

interface Props {
  code: string;
}

function prepMermaid(input: string): string {
  let code = input.replace(/^```mermaid\s*\n?/i, "").replace(/\n?```\s*$/, "");
  code = code.replace(/\[([^\]]+?)\]/g, (_, label: string) => {
    const t = label.trim();
    if ((t.startsWith('"') && t.endsWith('"')) || (t.startsWith("'") && t.endsWith("'"))) {
      return `[${label}]`;
    }
    return `["${label.replace(/"/g, '\\"')}"]`;
  });
  return code;
}

const MIN_ZOOM = 0.3;
const MAX_ZOOM = 3;
const ZOOM_STEP = 0.2;

export default function MermaidBlock({ code }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [svg, setSvg] = useState<string | null>(null);
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 });

  const containerRef = useRef<HTMLDivElement>(null);
  const dragging = useRef(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const offsetRef = useRef({ x: 0, y: 0 });

  // Global drag listeners — capture mouse events outside the container
  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      if (!dragging.current) return;
      const x = e.clientX - dragStart.current.x;
      const y = e.clientY - dragStart.current.y;
      offsetRef.current = { x, y };
      setOffset({ x, y });
    };
    const onUp = () => {
      dragging.current = false;
      if (containerRef.current) containerRef.current.style.cursor = "grab";
    };
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
    return () => {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const renderDiagram = async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, theme: "default", securityLevel: "loose" });
        const id = `m-${Math.random().toString(36).slice(2, 9)}`;
        const result = await mermaid.render(id, prepMermaid(code));
        if (!cancelled) {
          setSvg(result.svg);
          setZoom(1);
          setOffset({ x: 0, y: 0 });
          offsetRef.current = { x: 0, y: 0 };
        }
      } catch (e: any) {
        if (!cancelled) setError(e?.message || String(e));
      }
    };
    renderDiagram();
    return () => { cancelled = true; };
  }, [code]);

  const zoomIn = useCallback(() => setZoom((z) => Math.min(z + ZOOM_STEP, MAX_ZOOM)), []);
  const zoomOut = useCallback(() => setZoom((z) => Math.max(z - ZOOM_STEP, MIN_ZOOM)), []);
  const zoomReset = useCallback(() => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
    offsetRef.current = { x: 0, y: 0 };
  }, []);

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    setZoom((z) => Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, z - e.deltaY * 0.001)));
  }, []);

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    e.preventDefault();
    dragging.current = true;
    dragStart.current = { x: e.clientX - offsetRef.current.x, y: e.clientY - offsetRef.current.y };
    if (containerRef.current) containerRef.current.style.cursor = "grabbing";
  }, []);

  if (error) {
    return (
      <div className="my-2 p-3 bg-red-50 rounded-lg border border-red-200">
        <p className="text-xs text-red-600 mb-2">Mermaid: {error}</p>
        <pre className="text-xs text-gray-500 overflow-x-auto max-h-32">{code}</pre>
      </div>
    );
  }

  return (
    <div className="my-2 bg-white rounded-lg border border-gray-200">
      <div className="flex items-center justify-between px-3 py-1.5 border-b border-gray-100 bg-gray-50 rounded-t-lg">
        <span className="text-xs text-gray-500">思维导图 {Math.round(zoom * 100)}% · 拖拽移动</span>
        <div className="flex items-center gap-0.5">
          <button onClick={zoomOut} disabled={zoom <= MIN_ZOOM}
            className="p-1 rounded hover:bg-gray-200 disabled:opacity-30 transition-colors" title="缩小">
            <ZoomOut className="w-3.5 h-3.5 text-gray-600" />
          </button>
          <button onClick={zoomReset}
            className="p-1 rounded hover:bg-gray-200 transition-colors" title="重置">
            <RotateCcw className="w-3.5 h-3.5 text-gray-600" />
          </button>
          <button onClick={zoomIn} disabled={zoom >= MAX_ZOOM}
            className="p-1 rounded hover:bg-gray-200 disabled:opacity-30 transition-colors" title="放大">
            <ZoomIn className="w-3.5 h-3.5 text-gray-600" />
          </button>
        </div>
      </div>
      <div
        ref={containerRef}
        className="overflow-hidden max-h-[500px] cursor-grab"
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
      >
        {svg ? (
          <div
            className="flex justify-center p-4 min-w-max select-none"
            style={{
              transform: `translate(${offset.x}px, ${offset.y}px) scale(${zoom})`,
              transformOrigin: "top left",
            }}
            dangerouslySetInnerHTML={{ __html: svg }}
          />
        ) : (
          <div className="flex justify-center p-4 text-sm text-gray-400">渲染中...</div>
        )}
      </div>
    </div>
  );
}
