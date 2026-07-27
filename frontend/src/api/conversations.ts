import { apiRequest } from "./client";

interface ConversationApiResponse {
  id: number;
  customer_id: number;
  created_at: string;
  updated_at: string;
}

export interface Conversation {
  id: number;
  customerId: number;
  createdAt: string;
  updatedAt: string;
}
export interface RunAIResponse {
  conversation_id: number;
  status: string;
  message: string;
}

export async function runAI(
  conversationId: number
) {
  return apiRequest(
    `/customers/${conversationId}/run-ai`,
    {
      method: "POST",
    }
  );
}
export async function getConversations(
  customerId: number
): Promise<Conversation[]> {
  const conversations = await apiRequest<ConversationApiResponse[]>(
    `/customers/${customerId}/conversations`
  );

  return conversations.map((conversation) => ({
    id: conversation.id,
    customerId: conversation.customer_id,
    createdAt: conversation.created_at,
    updatedAt: conversation.updated_at,
  }));
}