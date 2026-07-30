import { apiRequest } from "./client";

export type MessageSender = "customer" | "company" | "ai"  | "system";

interface MessageApiResponse {
  id: number;
  conversation_id: number;
  sender: MessageSender;
  body: string;
  created_at: string;
}

export interface Message {
  id: number;
  conversationId: number;
  sender: MessageSender;
  text: string;
  createdAt: string;
}

interface CreateMessageRequest {
  sender: MessageSender;
  body: string;
}

function mapMessage(message: MessageApiResponse): Message {
  return {
    id: message.id,
    conversationId: message.conversation_id,
    sender: message.sender,
    text: message.body,
    createdAt: message.created_at,
  };
}

export async function getMessages(
  conversationId: number
): Promise<Message[]> {
  const messages = await apiRequest<MessageApiResponse[]>(
    `/conversations/${conversationId}/messages`
  );

  return messages.map(mapMessage);
}

export async function createMessage(
  conversationId: number,
  sender: MessageSender,
  text: string
): Promise<Message> {
  const createdMessage = await apiRequest<MessageApiResponse>(
    `/conversations/${conversationId}/messages`,
    {
      method: "POST",
      body: JSON.stringify({
        sender,
        body: text,
      } satisfies CreateMessageRequest),
    }
  );

  return mapMessage(createdMessage);
}

export async function clearConversationMessages(
  conversationId: number
): Promise<void> {
  await apiRequest<void>(
    `/conversations/${conversationId}/messages`,
    {
      method: "DELETE",
    }
  );
}