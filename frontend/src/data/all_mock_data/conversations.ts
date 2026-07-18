export interface Conversation {
  id: number;
  customerId: number;
  title: string;
}

export const conversations: Conversation[] = [
  {
    id: 1,
    customerId: 1,
    title: "Billing Question",
  },
  {
    id: 2,
    customerId: 2,
    title: "General Inquiry",
  },
];