import { useState } from "react";
import {
  Bot,
  Building2,
  MessageCircleMore,
  Play,
  Send,
  UserRound,
} from "lucide-react";

import type {
  Customer,
  Conversation,
  Message,
} from "../api";

interface ConversationWorkspaceProps {
  companySelected: boolean;
  customer: Customer | null;
  conversation: Conversation | null;
  messages: Message[];
  onSendCustomerMessage: (text: string) => Promise<void>;
  onSendCompanyMessage: (text: string) => Promise<void>;
  onRunAI: () => Promise<void>;
}

export function ConversationWorkspace({
  companySelected,
  customer,
  conversation,
  messages,
  onSendCustomerMessage,
  onSendCompanyMessage,
  onRunAI,
}: ConversationWorkspaceProps) {
  const [customerMessageText, setCustomerMessageText] = useState("");
  const [companyMessageText, setCompanyMessageText] = useState("");
  const [companyComposerOpen, setCompanyComposerOpen] = useState(false);

  const conversationSelected =
    customer !== null && conversation !== null;

  const handleCustomerMessageSubmit = async () => {
    const trimmedMessage = customerMessageText.trim();

    if (!conversationSelected || !trimmedMessage) {
      return;
    }

    try {
      await onSendCustomerMessage(trimmedMessage);
      setCustomerMessageText("");
    } catch (error) {
      console.error("Failed to send customer message:", error);
    }
  };

  const handleCompanyMessageSubmit = async () => {
    const trimmedMessage = companyMessageText.trim();

    if (!conversationSelected || !trimmedMessage) {
      return;
    }

    try {
      await onSendCompanyMessage(trimmedMessage);
      setCompanyMessageText("");
    } catch (error) {
      console.error("Failed to send company message:", error);
    }
  };

  return (
    <main className="conversation-workspace">
    <header className="conversation-header">
      <div>
        <span className="eyebrow">Conversation playground</span>

        <h2>
          {conversationSelected
            ? customer.name
            : companySelected
              ? "Select a customer conversation"
              : "No company selected"}
        </h2>

        <p>
          {conversationSelected
            ? `${customer.phone ?? "No phone number"} · Conversation #${conversation.id}`
            : companySelected
              ? "Choose a customer from the queue to open the conversation."
              : "Choose a company workspace to begin testing the AI workflow."}
        </p>
      </div>

      <button
        type="button"
        className="run-button"
        disabled={!conversationSelected}
        onClick={onRunAI}
      >
        <Play size={16} fill="currentColor" />
        Run AI
      </button>
    </header>
      <section
        className="message-stage"
        aria-label="Conversation messages"
      >
        {!conversationSelected ? (
          <div className="message-placeholder">
            <div className="placeholder-avatars" aria-hidden="true">
              <span>
                <UserRound size={22} />
              </span>

              <span>
                <Bot size={22} />
              </span>
            </div>

            <MessageCircleMore size={34} aria-hidden="true" />

            <h3>Conversation messages will appear here</h3>

            <p>
              Select a customer to view inbound customer messages and
              outbound company responses.
            </p>
          </div>
        ) : (
          <div className="message-list">
            {messages.length === 0 ? (
              <div className="empty-conversation">
                No messages have been added to this conversation.
              </div>
            ) : (
              messages.map((message) => (
                <div
                  key={message.id}
                  className={`message-row ${message.sender}`}
                >
                  <div className="message-bubble">
                    <div className="message-meta">
                      <span>
                        {message.sender === "customer"
                          ? customer.name
                          : message.sender === "company"
                            ? "Company Representative"
                            : "AI Assistant"}
                      </span>

                      <time dateTime={message.createdAt}>
                        {new Date(
                          message.createdAt
                        ).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </time>
                    </div>

                    <p>{message.text}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        )}
      </section>

      {conversationSelected && (
        <section className="company-reply-area">
          <button
            type="button"
            className={`company-reply-tab ${
              companyComposerOpen ? "active" : ""
            }`}
            onClick={() =>
              setCompanyComposerOpen((currentValue) => !currentValue)
            }
          >
            <Building2 size={15} />
            Send as company representative
          </button>

          {companyComposerOpen && (
            <form
              className="company-reply-composer"
              onSubmit={(event) => {
                event.preventDefault();
                handleCompanyMessageSubmit();
              }}
            >
              <textarea
                aria-label="Company representative message"
                value={companyMessageText}
                onChange={(event) =>
                  setCompanyMessageText(event.target.value)
                }
                placeholder="Write an outbound company response..."
              />

              <div className="company-reply-footer">
                <span>
                  This message will appear as an outbound response.
                </span>

                <button
                  type="submit"
                  disabled={!companyMessageText.trim()}
                >
                  <Send size={14} />
                  Send reply
                </button>
              </div>
            </form>
          )}
        </section>
      )}

      <footer className="composer-shell">
        <textarea
          aria-label="Customer message simulator"
          value={customerMessageText}
          onChange={(event) =>
            setCustomerMessageText(event.target.value)
          }
          placeholder={
            conversationSelected
              ? "Enter an inbound message as the customer..."
              : "Select a company and customer before entering a test message..."
          }
          disabled={!conversationSelected}
        />

        <div className="composer-footer">
          <span>
            {conversationSelected
              ? "Customer message simulator"
              : "Select a conversation to begin"}
          </span>

          <button
            type="button"
            disabled={
              !conversationSelected || !customerMessageText.trim()
            }
            onClick={() => {
              void handleCustomerMessageSubmit();
            }}          >
            Insert customer message
          </button>
        </div>
      </footer>
    </main>
  );
}