export type MessageSender = "customer" | "company" | "ai";

export interface Message {
  id: number;
  conversationId: number;
  sender: MessageSender;
  text: string;
  createdAt: string;
}

export const initialMessages: Message[] = [
  {
    id: 1,
    conversationId: 1,
    sender: "company",
    text: "Hello John! How can we help?",
    createdAt: "2026-07-12T17:30:00",
  },
  {
    id: 2,
    conversationId: 1,
    sender: "customer",
    text: "Why was I charged twice?",
    createdAt: "2026-07-12T17:32:00",
  },
];