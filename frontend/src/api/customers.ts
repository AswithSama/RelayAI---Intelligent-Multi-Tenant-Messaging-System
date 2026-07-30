import { apiRequest } from "./client";

export type QueueStatus = "review" | "completed";

interface CustomerApiResponse {
  id: number;
  company_id: number;
  name: string;
  phone: string | null;
  queue_status: QueueStatus;
  last_message: string | null;
  review_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface Customer {
  id: number;
  companyId: number;
  name: string;
  phone: string | null;
  queueStatus: QueueStatus;
  lastMessage: string | null;
  reviewReason: string | null;
  createdAt: string;
  updatedAt: string;
}

export async function getCustomers(
  companyId: number,
  queueStatus?: QueueStatus
): Promise<Customer[]> {
  const query = queueStatus
    ? `?queue_status=${encodeURIComponent(queueStatus)}`
    : "";

  const customers = await apiRequest<CustomerApiResponse[]>(
    `/companies/${companyId}/customers${query}`
  );

  return customers.map((customer) => ({
    id: customer.id,
    companyId: customer.company_id,
    name: customer.name,
    phone: customer.phone,
    queueStatus: customer.queue_status,
    lastMessage: customer.last_message,
    reviewReason: customer.review_reason,
    createdAt: customer.created_at,
    updatedAt: customer.updated_at,
  }));
}

export async function markCustomerCompleted(
  customerId: number
): Promise<Customer> {
  const customer = await apiRequest<CustomerApiResponse>(
    `/companies/customers/${customerId}/complete`,
    {
      method: "PATCH",
    }
  );

  return {
    id: customer.id,
    companyId: customer.company_id,
    name: customer.name,
    phone: customer.phone,
    queueStatus: customer.queue_status,
    lastMessage: customer.last_message,
    reviewReason: customer.review_reason,
    createdAt: customer.created_at,
    updatedAt: customer.updated_at,
  };
}