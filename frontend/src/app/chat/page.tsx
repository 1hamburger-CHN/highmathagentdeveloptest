"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import StreamingMarkdown from "@/components/chat/StreamingMarkdown";
import { Send, Loader2, Brain, BookOpen, Sparkles, History, Trash2, Copy, Check, Image as ImageIcon, X } from "lucide-react";

type Message = {
  role: "user" | "coach" | "system" | "animation";
  content: string;
  nodes?: string[];
  image?: string;  // base64 data URL for user messages with images
  plaintext?: boolean;
  title?: string;  // animation title
};

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

const NODE_LABELS: Record<string, { label: string; desc: string; icon: JSX.Element }> = {
  build_profile: { label: "构建画像", desc: "评估知识掌握情况、盲区和学习行为", icon: <Brain className="w-3 h-3" /> },
  diagnose: { label: "诊断错误", desc: "识别概念/计算/符号/逻辑/前置知识五类错误", icon: <Sparkles className="w-3 h-3" /> },
  coach: { label: "苏格拉底追问", desc: "L1/L2/L3分层提问，引导自主发现答案", icon: <BookOpen className="w-3 h-3" /> },
  generate: { label: "生成资源", desc: "生成讲义、练习题、思维导图或阅读材料", icon: <Sparkles className="w-3 h-3" /> },
  assess: { label: "评估回答", desc: "评估正确性并识别错误模式", icon: <Brain className="w-3 h-3" /> },
  quality_gate: { label: "质量把关", desc: "数学符号验证与内容安全检查", icon: <Sparkles className="w-3 h-3" /> },
};

// --- user identity helpers ---

function getUserId(): string {
  if (typeof window === "undefined") return "";
  let uid = localStorage.getItem("tutor_user_id");
  if (!uid) {
    uid = crypto.randomUUID?.() || Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("tutor_user_id", uid);
  }
  return uid;
}

function getSessionId(): string {
  if (typeof window === "undefined") return "";
  let sid = localStorage.getItem("tutor_session_id");
  if (!sid) {
    sid = crypto.randomUUID?.() || Math.random().toString(36).slice(2) + Date.now().toString(36);
    localStorage.setItem("tutor_session_id", sid);
  }
  return sid;
}

export default function ChatPage() {
  const [userId, setUserId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [profile, setProfile] = useState<Record<string, unknown> | null>(null);
  const [hasHistory, setHasHistory] = useState(false);
  const [historyLoaded, setHistoryLoaded] = useState(false);

  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const [activeNode, setActiveNode] = useState<string | null>(null);
  const [streamingContent, setStreamingContent] = useState("");
  const abortRef = useRef<AbortController | null>(null);

  const [debug, setDebug] = useState("");
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const [profileProgress, setProfileProgress] = useState<{ assessed: number; total: number } | null>(null);
  const [imageData, setImageData] = useState<string | null>(null);  // base64 data URL
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleCopy = useCallback((text: string, index: number) => {
    // navigator.clipboard requires HTTPS; fall back to execCommand for HTTP
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(() => {
        setCopiedIndex(index);
        setTimeout(() => setCopiedIndex(null), 1500);
      }).catch(() => {});
    } else {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.left = "-9999px";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); } catch (_) { /* noop */ }
      document.body.removeChild(ta);
      setCopiedIndex(index);
      setTimeout(() => setCopiedIndex(null), 1500);
    }
  }, []);

  // --- init: load identity, profile, and history on mount ---
  useEffect(() => {
    const uid = getUserId();
    setUserId(uid);
    setSessionId(getSessionId());

    // Load profile from backend
    fetch(`${API_BASE}/api/profile/${uid}`)
      .then((r) => r.json())
      .then((data) => {
        if (data.profile) {
          setProfile(data.profile);
          const km = (data.profile as Record<string, unknown>).knowledge_mastery as Array<{ score: number }> | undefined;
          if (km) {
            const assessed = km.filter((c) => c.score > 0).length;
            setProfileProgress({ assessed, total: 19 });
          }
        }
      })
      .catch(() => {});

    // Check if there's saved history
    fetch(`${API_BASE}/api/sessions/${uid}/latest`)
      .then((r) => r.json())
      .then((data) => {
        if (data.has_history) {
          setHasHistory(true);
        }
      })
      .catch(() => {});
  }, []);

  // --- load saved history ---
  const handleLoadHistory = useCallback(async () => {
    if (!userId) return;
    setDebug("加载历史对话中...");
    try {
      const resp = await fetch(`${API_BASE}/api/sessions/${userId}/latest`);
      const data = await resp.json();
      if (data.messages && data.messages.length > 0) {
        const msgs: Message[] = data.messages.map((m: { role: string; content: string; title?: string }) => ({
          role: m.role === "user" ? "user" : m.role === "animation" ? "animation" : "coach",
          content: m.content,
          title: m.title,
        }));
        setMessages(msgs);
        setHistoryLoaded(true);
        setHasHistory(false); // hide the load button after loading
        setDebug(`已加载 ${msgs.length} 条历史消息`);
      } else {
        setDebug("没有可加载的历史对话");
        setHasHistory(false);
      }
    } catch {
      setDebug("加载历史对话失败");
    }
  }, [userId]);

  // --- delete all records ---
  const handleDeleteAll = useCallback(async () => {
    if (!userId) return;
    if (!confirm("确认清除全部聊天记录和学习画像？此操作不可撤销。")) return;

    setDebug("清除中...");
    try {
      await fetch(`${API_BASE}/api/profile/${userId}`, { method: "DELETE" });
      await fetch(`${API_BASE}/api/sessions/${userId}`, { method: "DELETE" });

      // Reset local state
      localStorage.removeItem("tutor_user_id");
      const newUid = crypto.randomUUID?.() || Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem("tutor_user_id", newUid);
      setUserId(newUid);
      setSessionId(getSessionId());
      setProfile(null);
      setMessages([]);
      setHasHistory(false);
      setHistoryLoaded(false);
      setDebug("已清除全部记录");
    } catch {
      setDebug("清除失败");
    }
  }, [userId]);

  // --- image upload ---
  const handleImageUpload = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => setImageData(reader.result as string);
    reader.readAsDataURL(file);
  }, []);

  const handleRemoveImage = useCallback(() => {
    setImageData(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, []);

  // --- send message ---
  const handleSend = async () => {
    if ((!input.trim() && !imageData) || streaming) return;
    const userMessage = input.trim() || "请分析这张图片";
    const img = imageData;
    setInput("");
    setImageData(null);
    if (fileInputRef.current) fileInputRef.current.value = "";

    setMessages((prev) => [...prev, { role: "user", content: userMessage, image: img || undefined }]);
    setStreaming(true);
    setStreamingContent("");
    streamingRef.current = "";
    nodesRef.current = new Set();
    setDebug(`发送中: ${img ? "图片 + " : ""}${userMessage}`);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      // Build request: include identity, profile, and conversation history
      const body: Record<string, unknown> = {
        message: userMessage,
        user_id: userId,
        session_id: sessionId,
        profile: profile,
        history: messages.map((m) => ({ role: m.role === "user" ? "user" : "assistant", content: m.content })),
      };
      if (img) body.image = img;

      const resp = await fetch(`${API_BASE}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: controller.signal,
      });

      if (!resp.ok || !resp.body) throw new Error(`Connection failed: ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let chunkCount = 0;

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
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
          // Flush remaining streaming content
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

        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const eventText of events) {
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
    } catch (err: unknown) {
      if (err instanceof Error && err.name !== "AbortError") {
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

  const handleSSEEvent = (data: Record<string, unknown>) => {
    if (data.node) {
      setActiveNode(data.node as string);
      nodesRef.current.add(data.node as string);
    }
    // Profile progress update
    if (data.assessed !== undefined) {
      setProfileProgress({
        assessed: data.assessed as number,
        total: data.total_concepts as number,
      });
    }
    if (data.role && data.content) {
      // Animation resource — add directly as message
      if (data.role === "animation") {
        setMessages((msgs) => [...msgs, {
          role: "animation",
          content: data.content as string,
          title: (data.title as string) || "数学动画",
        }]);
        return;
      }
      streamingRef.current += data.content as string;
      setStreamingContent(streamingRef.current);
    }
    if (data.status === "complete") {
      const finalContent = streamingRef.current;
      const finalNodes = Array.from(nodesRef.current);
      if (finalContent) {
        setMessages((msgs) => [...msgs, { role: "coach", content: finalContent, nodes: finalNodes }]);
      }
      streamingRef.current = "";
      setStreamingContent("");
      nodesRef.current = new Set();

      // Persist updated profile from backend
      if (data.profile) {
        setProfile(data.profile as Record<string, unknown>);
        const km = (data.profile as Record<string, unknown>).knowledge_mastery as Array<{ score: number }> | undefined;
        if (km) {
          const assessed = km.filter((c) => c.score > 0).length;
          setProfileProgress({ assessed, total: 19 });
        }
      }
      setDebug("");
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
          <h1 className="text-lg font-semibold text-primary-900">
            苏格拉底教练
            <span className="ml-2 inline-flex rounded-md bg-primary-100 px-1.5 py-0.5 text-xs font-medium text-primary-700 align-middle">
              v2.0
            </span>
          </h1>
          <p className="text-xs text-gray-500">复变函数</p>
          {profileProgress && profileProgress.total > 0 && (
            <div className="mt-2 w-64">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-gray-500">
                  学习画像 {profileProgress.assessed}/{profileProgress.total} 概念
                </span>
                <span className="text-xs font-medium text-primary-600">
                  {Math.round((profileProgress.assessed / profileProgress.total) * 100)}%
                </span>
              </div>
              <div className="h-1.5 rounded-full bg-gray-200 overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary-500 transition-all duration-500 ease-out"
                  style={{ width: `${(profileProgress.assessed / profileProgress.total) * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
        <div className="flex items-center gap-2">
          {/* Load history button */}
          {hasHistory && !historyLoaded && (
            <button
              onClick={handleLoadHistory}
              className="flex items-center gap-1.5 rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800 hover:bg-amber-100 transition-colors"
            >
              <History className="w-3.5 h-3.5" />
              加载历史对话
            </button>
          )}
          {/* Delete all button */}
          <button
            onClick={handleDeleteAll}
            className="flex items-center gap-1.5 rounded-lg border border-red-200 bg-red-50 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-100 transition-colors"
          >
            <Trash2 className="w-3.5 h-3.5" />
            清除全部记录
          </button>
          {activeNode && NODE_LABELS[activeNode] && (
            <div className="flex items-center gap-1.5 rounded-full bg-primary-50 px-3 py-1 text-xs text-primary-700">
              {NODE_LABELS[activeNode].icon}
              <span>{NODE_LABELS[activeNode].label}</span>
              <Loader2 className="w-3 h-3 animate-spin" />
            </div>
          )}
        </div>
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
            <div className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}>
              <div
                className={`max-w-[75%] rounded-2xl px-4 py-3 break-words overflow-x-auto ${
                  m.role === "user"
                    ? "bg-primary-600 text-white"
                    : m.role === "system"
                    ? "bg-red-50 text-red-700 text-sm"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                {m.role === "animation" ? (
                  <div className="w-full max-w-[400px]">
                    <video
                      src={API_BASE + m.content}
                      controls
                      className="w-full rounded-lg"
                      preload="metadata"
                    >
                      您的浏览器不支持视频播放
                    </video>
                    {m.title && (
                      <p className="text-xs text-gray-500 mt-1 text-center">{m.title}</p>
                    )}
                  </div>
                ) : m.role === "coach" ? (
                  <>
                    {m.plaintext ? (
                      <div className="text-sm text-gray-900 whitespace-pre-wrap">{m.content}</div>
                    ) : (
                      <div className="prose prose-sm max-w-none text-gray-800 prose-headings:text-gray-900 prose-p:text-gray-800 prose-a:text-primary-600 prose-code:text-primary-700 prose-strong:text-gray-900 prose-li:text-gray-800 prose-blockquote:text-gray-700">
                        <StreamingMarkdown key={i} content={m.content} />
                      </div>
                    )}
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
                  <div>
                    {m.image && (
                      <img src={m.image} alt="uploaded" className="max-w-full rounded-lg mb-2 max-h-60 object-contain" />
                    )}
                    <p className="whitespace-pre-wrap">{m.content}</p>
                  </div>
                )}
              </div>
              {/* Copy button — always visible below the bubble */}
              <button
                onClick={() => handleCopy(m.content, i)}
                className="flex items-center gap-1 mt-1 px-2 py-1 rounded-md text-xs text-gray-400 hover:text-gray-600 hover:bg-gray-100 transition-colors"
                title="复制"
              >
                {copiedIndex === i ? (
                  <Check className="w-3.5 h-3.5 text-green-500" />
                ) : (
                  <Copy className="w-3.5 h-3.5" />
                )}
                {copiedIndex === i ? "已复制" : "复制"}
              </button>
            </div>
          </div>
        ))}

        {/* Streaming message */}
        {streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[75%] rounded-2xl bg-gray-100 px-4 py-3">
              <div className="prose prose-sm max-w-none text-gray-800 prose-headings:text-gray-900 prose-p:text-gray-800 prose-a:text-primary-600 prose-code:text-primary-700 prose-strong:text-gray-900 prose-li:text-gray-800 prose-blockquote:text-gray-700">
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
            <p className="text-sm">我会通过苏格拉底式追问，帮你发现复变函数中的盲区</p>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="border-t p-4">
        {/* Image preview */}
        {imageData && (
          <div className="max-w-3xl mx-auto mb-2 relative inline-block">
            <img src={imageData} alt="preview" className="max-h-32 rounded-lg border border-gray-300" />
            <button
              onClick={handleRemoveImage}
              className="absolute -top-1.5 -right-1.5 rounded-full bg-gray-700 text-white p-0.5 hover:bg-gray-900 transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
        <div className="flex gap-3 max-w-3xl mx-auto">
          {/* Image upload button */}
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            onChange={handleImageUpload}
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={streaming}
            className="rounded-xl border border-gray-300 px-3 py-3 text-gray-500 hover:bg-gray-50 hover:border-primary-300 transition-colors disabled:opacity-40"
            title="上传图片"
          >
            <ImageIcon className="w-5 h-5" />
          </button>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={imageData ? "描述你的图片问题... (Enter 发送)" : "输入你的问题或回答... (Enter 发送, Shift+Enter 换行)"}
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
              disabled={!input.trim() && !imageData || streaming}
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
