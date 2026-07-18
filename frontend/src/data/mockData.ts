export type QueueStatus = "review" | "completed";

export interface Company {
  id: string;
  name: string;
}

export interface QueueItem {
  id: string;
  companyId: string;
  customerName: string;
  phoneLabel: string;
  preview: string;
  timeLabel: string;
  status: QueueStatus;
  reason: string;
}

export const companies: Company[] = [
  { id: "northstar", name: "Northstar Home Services" },
  { id: "evergreen", name: "Evergreen Property Care" },
  { id: "clearview", name: "Clearview Service Group" },
  { id: "horizon", name: "Horizon Home Support" },
];

export const queueItems: QueueItem[] = [
  {
    id: "review-001",
    companyId: "northstar",
    customerName: "Maya Thompson",
    phoneLabel: "••• 0148",
    preview: "This is the third time the issue has returned. I need someone to call me.",
    timeLabel: "10:42 AM",
    status: "review",
    reason: "Complaint detected · Human follow-up required",
  },
  {
    id: "completed-001",
    companyId: "northstar",
    customerName: "Daniel Brooks",
    phoneLabel: "••• 8821",
    preview: "Yes, please add the service to my appointment next Tuesday.",
    timeLabel: "9:18 AM",
    status: "completed",
    reason: "Existing appointment located · Approved response prepared",
  },
];
