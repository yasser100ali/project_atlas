"use client";

import React from "react";
import { PreviewMessage, ThinkingMessage } from "@/components/message";
import { cn } from "@/lib/utils";
import { MultimodalInput } from "@/components/multimodal-input";
import { Overview } from "@/components/overview";
import { useScrollToBottom } from "@/hooks/use-scroll-to-bottom";
import { ToolInvocation } from "ai";
import type { Message, CreateMessage, ChatRequestOptions } from "ai";
type Role = "user" | "assistant" | "system";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { RotateCcw } from "lucide-react";
import { ThemeToggle } from "@/components/theme-toggle";

export function Chat() {
  const chatId = "001";

  const [messages, setMessages] = React.useState<Array<Message>>([]);
  const [input, setInput] = React.useState("");
  const [isLoading, setIsLoading] = React.useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = React.useState(false);
  const thinkingLogsByIdRef = React.useRef<Record<string, string[]>>({});
  const resumeByIdRef = React.useRef<Record<string, { url: string; name: string; contentType: string } | null>>({});

  // Remove startup test once verified

  const append = async (
    message: Message | CreateMessage,
    _opts?: ChatRequestOptions,
  ): Promise<string> => {
    const id = (message as Message).id || `${Date.now()}`;
    const normalized: Message = {
      id,
      role: (message as any).role,
      content: String((message as any).content ?? ""),
    } as Message;
    setMessages((prev) => [...prev, normalized]);
    return id;
  };

  const stop = () => {
    // no-op placeholder
  };

  const handleSubmit = async (
    _event?: { preventDefault?: () => void },
    chatRequestOptions?: { contentOverride?: string; data?: any },
  ) => {
    const override = chatRequestOptions?.contentOverride;
    const contentToSend =
      typeof override === "string" && override.trim().length > 0
        ? override
        : input;

    if (!contentToSend.trim()) return;
    // clear input immediately (for UI) if we were using it
    setInput("");
    const userMessage: Message = {
      id: `${Date.now()}`,
      role: "user",
      content: contentToSend,
    } as Message;
    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    const attachments = chatRequestOptions?.data?.attachments || [];

    const requestBody = {
      messages: [
        ...messages.map((m) => ({ role: m.role as Role, content: String(m.content) })),
        { role: "user" as Role, content: contentToSend },
      ],
      data: { attachments },
      chatId,
    };

    // Prepare assistant placeholder to attach thinking logs to
    const assistantId = `${Date.now()}-assistant`;
    thinkingLogsByIdRef.current[assistantId] = [];

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(requestBody),
      });

      if (!res.body) {
        throw new Error("No response body");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      // Insert assistant placeholder
      setMessages((prev) => [
        ...prev,
        { id: assistantId, role: "assistant", content: "" } as Message,
      ]);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const evt = JSON.parse(trimmed);
            if (evt.event === "thinking") {
              const msg = typeof evt.data === "string" ? evt.data : JSON.stringify(evt.data);
              thinkingLogsByIdRef.current[assistantId].push(msg);
            } else if (evt.event === "resume_ready") {
              const { url, name, contentType } = evt.data || {};
              // Only store; attach after final to avoid duplicates during stream
              resumeByIdRef.current[assistantId] = { url, name, contentType };
            } else if (evt.event === "final") {
              const content = typeof evt.response === "string" ? evt.response : JSON.stringify(evt.response);
              const resume = resumeByIdRef.current[assistantId];
              setMessages((prev) => prev.map((m) => {
                if (m.id !== assistantId) return m;
                if (!resume) return { ...m, content } as Message;
                const existing = (m.experimental_attachments || []) as any[];
                const deduped = existing.filter((a) => a.url !== resume.url);
                return {
                  ...m,
                  content,
                  experimental_attachments: [...deduped, resume as any],
                } as Message;
              }));
            } else if (evt.event === "error") {
              const errText = evt.message || "Unknown error";
              setMessages((prev) => prev.map((m) => (m.id === assistantId ? { ...m, content: `Error: ${errText}` } : m)));
            }
          } catch {
            // ignore bad lines
          }
        }
      }
    } catch (e: any) {
      toast.error(e?.message || "Streaming failed");
    } finally {
      setIsLoading(false);
      // ensure textbox remains cleared after stream finishes
      setInput("");
    }
  };

  const [messagesContainerRef, messagesEndRef] =
    useScrollToBottom<HTMLDivElement>(140);

  return (
    <div className="flex min-h-[100dvh] bg-background">
      {/* Left sidebar sliver with border; expands on toggle */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex flex-col border-r bg-background/95 backdrop-blur transition-[width] duration-200",
          isSidebarOpen ? "w-56" : "w-16",
        )}
      >
        {/* Removed duplicate top toggle */}
        <div className="p-3 flex flex-col gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            className="rounded-full px-3 py-1 text-xs shadow-sm bg-background/70 backdrop-blur border-border hover:bg-accent gap-1.5"
            onClick={async () => {
              try {
                await fetch("/api/session/reset", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ chatId }) });
                setMessages([]);
                toast.success("New session started");
              } catch (e: any) {
                toast.error(e?.message || "Failed to reset session");
              }
            }}
          >
            <RotateCcw className="size-3" />
            {isSidebarOpen ? "New session" : ""}
          </Button>
          <ThemeToggle asButton expanded={isSidebarOpen} />
        </div>
        <div className="mt-auto p-2 w-full flex justify-center pl-1">
          <Button
            type="button"
            size="icon"
            variant="outline"
            className="rounded-full h-8 w-8"
            onClick={() => setIsSidebarOpen((v) => !v)}
            aria-label="Toggle sidebar"
          >
            <span className="text-lg leading-none">{isSidebarOpen ? "⟨" : "⟩"}</span>
          </Button>
        </div>
      </aside>

      {/* Main area that respects the sidebar width */}
      <main className={cn("flex flex-col min-w-0 flex-1 min-h-[100dvh]", isSidebarOpen ? "ml-56" : "ml-16")}> 
        <div
          ref={messagesContainerRef}
          className="flex flex-col min-w-0 flex-1 gap-6 pt-4 pb-40"
        >
          {messages.length === 0 && <Overview />}

          {messages.map((message: Message, index: number) => (
            <PreviewMessage
              key={message.id}
              chatId={chatId}
              message={message}
              isLoading={isLoading && messages.length - 1 === index}
              thinkingLogs={thinkingLogsByIdRef.current[message.id]}
            />
          ))}

          {isLoading &&
            messages.length > 0 &&
            messages[messages.length - 1].role === "user" && <ThinkingMessage />}

          <div
            ref={messagesEndRef}
            className="shrink-0 min-w-[24px] min-h-[24px]"
          />
        </div>

        <form className="flex sticky bottom-0 z-40 mx-auto px-4 bg-background pb-4 md:pb-6 gap-2 w-full md:max-w-3xl">
          <MultimodalInput
            chatId={chatId}
            input={input}
            setInput={setInput}
            handleSubmit={handleSubmit}
            isLoading={isLoading}
            stop={stop}
            messages={messages}
            setMessages={setMessages}
            append={append}
          />
        </form>
      </main>
    </div>
  );
}
