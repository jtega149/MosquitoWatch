"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { MessageCircle, Send, X } from "lucide-react";
import { ApiError, fetchChat } from "@/lib/api";

type ChatMessage = {
  role: "user" | "assistant";
  text: string;
  cached?: boolean;
  similarity?: number | null;
};

const STARTER: ChatMessage = {
  role: "assistant",
  text: "Ask how MosquitoWatch works, which ZIP currently looks highest risk, or general West Nile virus facts. I am not a doctor.",
};

export function ChatWidget() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([STARTER]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, open]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message || pending) return;

    setInput("");
    setPending(true);
    setMessages((current) => [...current, { role: "user", text: message }]);
    try {
      const result = await fetchChat(message);
      setMessages((current) => [
        ...current,
        {
          role: "assistant",
          text: result.reply,
          cached: result.cached,
          similarity: result.similarity,
        },
      ]);
    } catch (err) {
      const detail =
        err instanceof ApiError
          ? err.message
          : "Chat is unavailable. Confirm the API and Redis are running.";
      setMessages((current) => [...current, { role: "assistant", text: detail }]);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="fixed bottom-5 left-5 z-50">
      {open && (
        <section
          aria-label="MosquitoWatch assistant"
          className="mb-3 flex h-[min(28rem,70vh)] w-[min(22rem,calc(100vw-2.5rem))] flex-col overflow-hidden rounded-2xl border border-white/10 bg-[#0c1220] shadow-[0_16px_48px_rgba(0,0,0,0.45)]"
        >
          <header className="flex items-center justify-between border-b border-white/8 bg-[#131a2b] px-4 py-3">
            <div>
              <div className="text-sm font-semibold text-white">Ask MosquitoWatch</div>
              <div className="text-[11px] text-slate-400">Gemini RAG · semantic cache</div>
            </div>
            <button
              type="button"
              onClick={() => setOpen(false)}
              aria-label="Close chat"
              className="rounded-lg p-1 text-slate-400 hover:bg-white/5 hover:text-white"
            >
              <X className="h-4 w-4" />
            </button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto px-3 py-3">
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                <div
                  className={`max-w-[90%] rounded-2xl px-3 py-2 text-sm leading-relaxed ${
                    message.role === "user"
                      ? "bg-[#22c55e] text-[#052e16]"
                      : "border border-white/10 bg-[#131a2b] text-slate-200"
                  }`}
                >
                  {message.role === "assistant" && message.cached && (
                    <div className="mb-1 text-[10px] font-medium uppercase tracking-wider text-[#4ade80]">
                      Cache hit
                      {message.similarity != null
                        ? ` · ${message.similarity.toFixed(2)} similarity`
                        : ""}
                    </div>
                  )}
                  {message.text}
                </div>
              </div>
            ))}
            {pending && (
              <div className="text-xs text-slate-500">Retrieving context…</div>
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={onSubmit} className="border-t border-white/8 p-3">
            <div className="flex gap-2">
              <input
                value={input}
                onChange={(event) => setInput(event.target.value)}
                maxLength={500}
                placeholder="Ask a question"
                aria-label="Chat message"
                className="min-w-0 flex-1 rounded-xl border border-white/10 bg-[#0a0e1a] px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500 focus:border-[#22c55e]/60"
              />
              <button
                type="submit"
                disabled={pending || !input.trim()}
                aria-label="Send message"
                className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#22c55e] text-[#052e16] disabled:opacity-40"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </form>
        </section>
      )}

      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Close chat" : "Open chat"}
        aria-expanded={open}
        className="flex h-14 w-14 items-center justify-center rounded-full bg-[#22c55e] text-[#052e16] shadow-[0_0_24px_rgba(34,197,94,0.45)] hover:bg-[#16a34a]"
      >
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
      </button>
    </div>
  );
}
