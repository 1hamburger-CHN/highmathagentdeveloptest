"use client";

import { useRef, useState } from "react";
import StreamingMarkdown from "@/components/chat/StreamingMarkdown";
import { Send, Loader2, Brain, BookOpen, Sparkles } from "lucide-react";

type Message = {
  role: "user" | "coach" | "system";
  content: string;
  nodes?: string[];
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const NODE_LABELS: Record<string, { label: string; desc: string; icon: JSX.Element }> = {
  build_profile: { label: "构建画像", desc: "评估知识掌握情况、盲区和学习行为", icon: <Brain className="w-3 h-3" /> },
  diagnose: { label: "诊断错误", desc: "识别概念/计算/符号/逻辑/前置知识五类错误", icon: <Sparkles className="w-3 h-3" /> },
  coach: { label: "苏格拉底追问", desc: "L1/L2/L3分层提问，引导自主发现答案", icon: <BookOpen className="w-3 h-3" /> },
  generate: { label: "生成资源", desc: "生成讲义、练习题、思维导图或阅读材料", icon: <Sparkles className="w-3 h-3" /> },
  assess: { label: "评估回答", desc: "评估正确性并识别错误模式", icon: <Brain className="w-3 h-3" /> },
  quality_gate: { label: "质量把关", desc: "数学符号验证与内容安全检查", icon: <Sparkles className="w-3 h-3" /> },
};

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const [debug, setDebug] = useState("");

  const handleSend = async () => {
    if (!input.trim()) { setDebug("输入为空"); return; }
    if (streaming) { setDebug("正在流式输出中"); return; }
    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setStreaming(true);
    setStreamingContent("");
    streamingRef.current = "";
    nodesRef.current = new Set();
    setDebug(`发送中: ${userMessage}`);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch(`${API_BASE}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage }),
        signal: controller.signal,
      });

      setDebug(`连接成功, status=${resp.status}`);
      if (!resp.ok || !resp.body) throw new Error(`Connection failed: ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let chunkCount = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          // Process any remaining data in buffer before breaking
          if (buffer.trim()) {
            const remaining = buffer.split("\n\n");
            for (const eventText of remaining) {
              if (!eventText.trim()) continue;
              for (const line of eventText.split("\n")) {
                if (line.startsWith("data: ")) {
                  try {
                    const data = JSON.parse(line.slice(6).trim());
                    handleSSEEvent(data);
                  } catch { /* skip */ }
                }
              }
            }
          }
          setDebug(`流结束, 共${chunkCount}块, msgs=${streamingRef.current.length}字`);
          // flush any remaining streaming content
          if (streamingRef.current) {
            setMessages((msgs) => [...msgs, { role: "coach", content: streamingRef.current, nodes: Array.from(nodesRef.current) }]);
            streamingRef.current = "";
            setStreamingContent("");
            nodesRef.current = new Set();
          }
          break;
        }
        chunkCount++;
        const text = decoder.decode(value, { stream: true });
        buffer += text;
        setDebug(`块#${chunkCount}: +${text.length}B`);

        // Parse SSE events using \n\n as event delimiter
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventText of events) {
          if (!eventText.trim()) continue;
          const lines = eventText.split("\n");
          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith("data: ")) {
              try {
                const data = JSON.parse(trimmed.slice(6));
                handleSSEEvent(data);
              } catch {
                setDebug(`JSON解析失败: ${trimmed.slice(0, 60)}`);
              }
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setDebug(`错误: ${err.message}`);
        setMessages((prev) => [...prev, { role: "system", content: `连接失败: ${err.message}` }]);
      }
    } finally {
      setStreaming(false);
      setActiveNode(null);
      abortRef.current = null;
    }
  };

  const streamingRef = useRef("");
  const nodesRef = useRef<Set<string>>(new Set());

  const handleSSEEvent = (data: any) => {
    if (data.node) {
      setActiveNode(data.node);
      nodesRef.current.add(data.node);
    }
    if (data.role && data.content) {
      streamingRef.current += data.content;
      setStreamingContent(streamingRef.current);
    }
    if (data.status === "complete") {
      setDebug(`完成, 总消息=${streamingRef.current.length}字`);
      const finalContent = streamingRef.current;
      const finalNodes = Array.from(nodesRef.current);
      if (finalContent) {
        setMessages((msgs) => [...msgs, { role: "coach", content: finalContent, nodes: finalNodes }]);
      }
      streamingRef.current = "";
      setStreamingContent("");
      nodesRef.current = new Set();
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

      {/* Debug bar */}
      {debug && (
        <div className="bg-yellow-100 px-4 py-1 text-xs text-yellow-800 font-mono">
          DEBUG: {debug}
        </div>
      )}

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
                <>
                  <div className="prose prose-sm max-w-none prose-headings:text-gray-900 prose-p:text-gray-800">
                    <StreamingMarkdown content={m.content} />
                  </div>
                  {m.nodes && m.nodes.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-gray-200">
                      {m.nodes.map((n) => {
                        const info = NODE_LABELS[n];
                        if (!info) return null;
                        return (
                          <span
                            key={n}
                            title={info.desc}
                            className="inline-flex items-center gap-1 rounded-full bg-primary-50 px-2 py-0.5 text-xs text-primary-700 cursor-help"
                          >
                            {info.icon}
                            <span>{info.label}</span>
                          </span>
                        );
                      })}
                    </div>
                  )}
                </>
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
              disabled={streaming}
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
