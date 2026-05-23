"use client";

import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import MermaidBlock from "./MermaidBlock";
import "katex/dist/katex.min.css";

interface Props {
  content: string;
}

export default function StreamingMarkdown({ content }: Props) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={{
        code({ className, children, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const language = match?.[1];
          const codeStr = String(children).replace(/\n$/, "");

          if (language === "mermaid") {
            return <MermaidBlock code={codeStr} />;
          }

          // Inline code (no language)
          if (!language) {
            return (
              <code className="bg-gray-100 text-primary-700 px-1 py-0.5 rounded text-sm" {...props}>
                {children}
              </code>
            );
          }

          // Regular code block
          return (
            <pre className="bg-gray-900 text-gray-100 rounded-lg p-3 overflow-x-auto text-sm">
              <code className={className} {...props}>
                {children}
              </code>
            </pre>
          );
        },
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
