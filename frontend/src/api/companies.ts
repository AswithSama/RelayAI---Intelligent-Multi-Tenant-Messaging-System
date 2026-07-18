import { apiRequest } from "./client";

export interface Company {
  id: number;
  name: string;
  created_at: string;
  updated_at: string;
}

export function getCompanies(): Promise<Company[]> {
  return apiRequest<Company[]>("/companies");
}