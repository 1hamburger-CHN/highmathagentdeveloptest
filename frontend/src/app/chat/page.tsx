"use client";

import { useRef, useState } from "react";
import StreamingMarkdown from "@/components/chat/StreamingMarkdown";
import { Send, Loader2, Brain, BookOpen, Sparkles } from "lucide-react";

type Message = {
  role: "user" | "coach" | "system";
  content: string;
  node?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const NODE_LABELS: Record<string, { label: string; icon: JSX.Element }> = {
  build_profile: { label: "构建画像", icon: <Brain className="w-3 h-3" /> },
  diagnose: { label: "诊断中", icon: <Sparkles className="w-3 h-3" /> },
  coach: { label: "苏格拉底追问", icon: <BookOpen className="w-3 h-3" /> },
  generate: { label: "生成资源", icon: <Sparkles className="w-3 h-3" /> },
  assess: { label: "评估中", icon: <Brain className="w-3 h-3" /> },
  quality_gate: { label: "质量把关", icon: <Sparkles className="w-3 h-3" /> },
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const handleSend = async () => {
    if (!input.trim() || streaming) return;
    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setStreaming(true);
    setStreamingContent("");

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch(`${API_BASE}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) throw new Error("Connection failed");

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Parse SSE events using \n\n as event delimiter
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventText of events) {
          const lines = eventText.split("\n");
          let eventType = "";
          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.slice(7).trim();
            } else if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));
                handleSSEEvent(data);
              } catch {
                // Malformed JSON, skip this event
              }
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setMessages((prev) => [...prev, { role: "system", content: `连接失败: ${err.message}` }]);
      }
    } finally {
      setStreaming(false);
      setActiveNode(null);
      setStreamingContent("");
      abortRef.current = null;
    }
  };

  const handleSSEEvent = (data: any) => {
    if (data.node) setActiveNode(data.node);
    if (data.role && data.content) {
      setStreamingContent((prev) => prev + data.content);
    }
    if (data.status === "complete") {
      // Flush streaming content as a message
      setStreamingContent((prev) => {
        if (prev) {
          setMessages((msgs) => [...msgs, { role: "coach", content: prev }]);
        }
        return "";
      });
    }
  };

  const handleStop = () => {
    abortRef.current?.abort();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-screen flex-col bg-white">
      {/* Header */}
      <header className="flex items-center justify-between border-b px-6 py-3">
        <div>
          <h1 className="text-lg font-semibold text-primary-900">苏格拉底教练</h1>
          <p className="text-xs text-gray-500">高等数学 · 极限与连续</p>
        </div>
        {activeNode && NODE_LABELS[activeNode] && (
          <div className="flex items-center gap-1.5 rounded-full bg-primary-50 px-3 py-1 text-xs text-primary-700">
            {NODE_LABELS[activeNode].icon}
            <span>{NODE_LABELS[activeNode].label}</span>
            <Loader2 className="w-3 h-3 animate-spin" />
          </div>
        )}
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-3 ${
                m.role === "user"
                  ? "bg-primary-600 text-white"
                  : m.role === "system"
                  ? "bg-red-50 text-red-700 text-sm"
                  : "bg-gray-100 text-gray-900"
              }`}
            >
              {m.role === "coach" ? (
                <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-800">
                  <StreamingMarkdown content={m.content} />
                </div>
              ) : (
                <p className="whitespace-pre-wrap">{m.content}</p>
              )}
            </div>
          </div>
        ))}

        {/* Streaming message */}
        {streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[75%] rounded-2xl bg-gray-100 px-4 py-3">
              <div className="prose prose-sm max-w-none">
                <StreamingMarkdown content={streamingContent} />
              </div>
            </div>
          </div>
        )}

        {/* Empty state */}
        {messages.length === 0 && !streamingContent && (
          <div className="flex h-full flex-col items-center justify-center text-gray-400 gap-3">
            <BookOpen className="w-12 h-12 text-primary-200" />
            <p className="text-lg">开始你的数学探索吧...</p>
            <p className="text-sm">我会通过苏格拉底式追问，帮你发现极限与连续中的盲区</p>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t p-4">
        <div className="flex gap-3 max-w-3xl mx-auto">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入你的问题或回答... (Enter 发送, Shift+Enter 换行)"
            rows={1}
            className="flex-1 resize-none rounded-xl border border-gray-300 px-4 py-3 focus:border-primary-500 focus:outline-none focus:ring-2 focus:ring-primary-200"
            disabled={streaming}
          />
          {streaming ? (
            <button
              onClick={handleStop}
              className="rounded-xl bg-red-500 px-5 py-3 font-semibold text-white hover:bg-red-600 transition-colors"
            >
              停止
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="rounded-xl bg-primary-600 px-5 py-3 font-semibold text-white hover:bg-primary-700 transition-colors disabled:opacity-40"
            >
              <Send className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
