import { AlertTriangle, CheckCircle2, MessageSquareText } from "lucide-react";
import type { Customer } from "../api";
type QueueStatus = "review" | "completed";

interface QueuePanelProps {
  customers: Customer[];
  activeTab: QueueStatus;
  onTabChange: (tab: QueueStatus) => void;
  companySelected: boolean;
  selectedCustomerId: number | null;
  onCustomerSelect: (id: number) => void;
}

const TAB_LABELS: Record<QueueStatus, string> = {
  review: "Needs Review",
  completed: "Completed",
};

export function QueuePanel({
  activeTab,
  onTabChange,
  customers,
  companySelected,
  selectedCustomerId,
  onCustomerSelect,
}: QueuePanelProps) {
  const visibleCustomers = customers.filter(
    (customer) => customer.queueStatus === activeTab
  );

  return (
    <aside className="queue-panel" aria-label="Workflow Queue">
      <div className="queue-tabs" role="tablist">
        {(Object.keys(TAB_LABELS) as QueueStatus[]).map((tab) => {
          const count = customers.filter(
            (customer) => customer.queueStatus === tab
          ).length;

          return (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={activeTab === tab}
              className={`queue-tab ${
                activeTab === tab ? "active" : ""
              }`}
              onClick={() => onTabChange(tab)}
            >
              {TAB_LABELS[tab]}
              <span>{count}</span>
            </button>
          );
        })}
      </div>

      <div className="queue-list">
        {!companySelected ? (
          <div className="queue-empty">
            <MessageSquareText size={26} />
            <strong>Select a company</strong>
            <p>Customers will appear here.</p>
          </div>
        ) : visibleCustomers.length === 0 ? (
          <div className="queue-empty compact">
            <strong>No customers</strong>
            <p>No conversations found in this queue.</p>
          </div>
        ) : (
          visibleCustomers.map((customer) => (
            <button
              key={customer.id}
              type="button"
              onClick={() => onCustomerSelect(customer.id)}
              className={`queue-card ${
                selectedCustomerId === customer.id ? "selected" : ""
              }`}
            >
              <div className="queue-card-header">
                <span className={`status-icon ${customer.queueStatus}`}>
                  {customer.queueStatus === "review" ? (
                    <AlertTriangle size={16} />
                  ) : (
                    <CheckCircle2 size={16} />
                  )}
                </span>

                <div>
                  <strong>{customer.name}</strong>
                  <small>{customer.phone}</small>
                </div>

                <time>{customer.lastMessage}</time>
              </div>

              <p>{customer.lastMessage}</p>

              {customer.queueStatus === "review" &&
                customer.reviewReason && (
                  <div className="queue-reason">
                    {customer.reviewReason}
                  </div>
                )}
            </button>
          ))
        )}
      </div>
    </aside>
  );
}