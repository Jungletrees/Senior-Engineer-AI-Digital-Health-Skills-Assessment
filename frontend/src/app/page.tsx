"use client";

import { FormEvent, useMemo, useState } from "react";
import { getApiBaseUrl } from "../lib/documentsCore";

type Citation = {
  number: number;
  document_title: string;
  page_number: number | null;
  section_path: string | null;
  snippet: string | null;
};

type ChatMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

type ChatResponse = {
  session_id: string;
  answer: string;
  citations?: Citation[];
  cache_status: string;
  output_filter_status: string;
};

const sampleQuestions = [
  "What does the uploaded guidance say about dosing?",
  "Summarize the table on the cited page.",
  "What evidence supports the recommendation?",
];

export default function HomePage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome",
      role: "assistant",
      content:
        "I answer from indexed PDFs only. Upload a document, then ask a question and I will return grounded citations when source chunks support the answer.",
    },
  ]);
  const [status, setStatus] = useState("Ready");
  const [isSending, setIsSending] = useState(false);

  const hasCitations = useMemo(
    () => messages.some((message) => (message.citations || []).length > 0),
    [messages],
  );

  async function submitQuestion(event?: FormEvent<HTMLFormElement>, forcedQuestion?: string) {
    event?.preventDefault();
    const question = (forcedQuestion || input).trim();
    if (!question || isSending) {
      return;
    }

    setInput("");
    setIsSending(true);
    setStatus("Retrieving grounded context");
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: question,
    };
    setMessages((current) => [...current, userMessage]);

    try {
      const response = await postChat(question, sessionId);
      setSessionId(response.session_id);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: response.answer,
          citations: response.citations || [],
        },
      ]);
      setStatus(response.output_filter_status === "passed" ? `Grounded response · ${response.cache_status}` : "Filtered");
    } catch {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "The chat service is unavailable. Confirm FastAPI is running on port 6100.",
        },
      ]);
      setStatus("Backend unavailable");
    } finally {
      setIsSending(false);
    }
  }

  return (
    <main className="rag-workspace">
      <aside className="rag-sidebar">
        <div>
          <p className="app-kicker">Last Mile Health RAG</p>
          <h1>Document-grounded chat</h1>
          <p>
            Ask questions against indexed PDFs. Answers are filtered for grounding and show citations when
            retrieved chunks support the response.
          </p>
        </div>

        <nav className="workspace-links" aria-label="Workspace links">
          <a href="/documents">Documents</a>
          <a href="http://localhost:8000">Chainlit</a>
          <a href="http://localhost:6100/docs">API docs</a>
          <a href="http://localhost:6100/health">Health</a>
        </nav>

        <div className="grounding-panel">
          <span>Status</span>
          <strong>{status}</strong>
          <small>{hasCitations ? "Latest answers include source notes." : "Citations appear after retrieval."}</small>
        </div>
      </aside>

      <section className="chat-surface" aria-label="RAG chat">
        <div className="chat-transcript">
          {messages.map((message) => (
            <article key={message.id} className={`chat-message message-${message.role}`}>
              <div className="message-label">{message.role === "user" ? "You" : "RAG assistant"}</div>
              <p>
                {message.content}
                {message.citations?.length ? renderCitationMarkers(message.citations) : null}
              </p>
              {message.citations?.length ? (
                <ol className="citation-notes" aria-label="Citations">
                  {message.citations.map((citation) => (
                    <li key={`${message.id}-${citation.number}`}>
                      <span>{citation.document_title}</span>
                      {citation.page_number ? <span>, p. {citation.page_number}</span> : null}
                      {citation.section_path ? <span>, {citation.section_path}</span> : null}
                    </li>
                  ))}
                </ol>
              ) : null}
            </article>
          ))}
        </div>

        <div className="prompt-row" aria-label="Suggested questions">
          {sampleQuestions.map((question) => (
            <button key={question} type="button" onClick={() => submitQuestion(undefined, question)}>
              {question}
            </button>
          ))}
        </div>

        <form className="chat-composer" onSubmit={submitQuestion}>
          <label htmlFor="chat-input">Message</label>
          <textarea
            id="chat-input"
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder="Ask a question about an uploaded document..."
            rows={3}
          />
          <button type="submit" disabled={isSending || !input.trim()}>
            {isSending ? "Sending" : "Send"}
          </button>
        </form>
      </section>
    </main>
  );
}

async function postChat(message: string, sessionId: string | null): Promise<ChatResponse> {
  const response = await fetch(`${getApiBaseUrl()}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      message,
      ...(sessionId ? { session_id: sessionId } : {}),
    }),
  });
  if (!response.ok) {
    throw new Error(`Chat failed with ${response.status}`);
  }
  return response.json();
}

function renderCitationMarkers(citations: Citation[]) {
  return citations.map((citation) => (
    <sup key={citation.number}>{toSuperscript(citation.number)}</sup>
  ));
}

function toSuperscript(value: number) {
  const digits: Record<string, string> = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
  };
  return String(value)
    .split("")
    .map((character) => digits[character] || character)
    .join("");
}
