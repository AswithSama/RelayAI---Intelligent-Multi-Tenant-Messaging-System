export type CustomerStatus = "review" | "completed";

export interface Customer {
  id: number;
  companyId: number;
  name: string;
  phone: string;
  status: CustomerStatus;
  lastUpdated: string;
  lastMessage: string;
  reason: string;
}

export const customers: Customer[] = [
  {
    id: 1,
    companyId: 1,
    name: "John Smith",
    phone: "(555) 201-1133",
    status: "review",
    lastUpdated: "2 min ago",
    lastMessage: "Why was I charged twice?",
    reason: "Billing issue requires review",
  },
  {
    id: 2,
    companyId: 1,
    name: "Emily Johnson",
    phone: "(555) 201-2234",
    status: "completed",
    lastUpdated: "1 hr ago",
    lastMessage: "Thank you for the update.",
    reason: "Conversation completed",
  },
];