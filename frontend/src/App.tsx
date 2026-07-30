import { useEffect, useMemo, useState, useRef } from "react";
import { Activity, FlaskConical } from "lucide-react";

import { CompanySelector } from "./components/CompanySelector";
import { ConversationWorkspace } from "./components/ConversationWorkspace";
import { QueuePanel } from "./components/QueuePanel";

import {
  clearConversationMessages,
  createMessage,
  getCompanies,
  getCustomers,
  getConversations,
  getMessages,
  markCustomerCompleted,
  type Company,
  type Customer,
  type Conversation,
  type Message,
  type MessageSender,
  type QueueStatus,
} from "./api";

export default function App() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);

  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(
    null
  );

  const [selectedCustomerId, setSelectedCustomerId] = useState<number | null>(
    null
  );

  const [activeTab, setActiveTab] = useState<QueueStatus>("review");

  const [companiesLoading, setCompaniesLoading] = useState(true);
  const [customersLoading, setCustomersLoading] = useState(false);
  const [conversationLoading, setConversationLoading] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);

  const [companiesError, setCompaniesError] = useState<string | null>(null);
  const [customersError, setCustomersError] = useState<string | null>(null);
  const [conversationError, setConversationError] = useState<string | null>(
    null
  );
  const [messagesError, setMessagesError] = useState<string | null>(null);
  const [aiResponsePending, setAiResponsePending] = useState(false);
  const [aiResponseError, setAiResponseError] = useState<string | null>(
    null
  );
  const aiPollingTimerRef = useRef<number | null>(null);
  const preserveSelectedConversationRef = useRef(false);
  const handleMarkCompleted = async (): Promise<void> => {
  if (
    selectedCompanyId === null ||
    selectedCustomerId === null
  ) {
    return;
  }

  try {
    await markCustomerCompleted(selectedCustomerId);

    const completedCustomers = await getCustomers(
      selectedCompanyId,
      "completed"
    );

    preserveSelectedConversationRef.current = true;

    setCustomers(completedCustomers);
    setActiveTab("completed");
    setAiResponseError(null);
  } catch (error) {
    console.error(
      "Failed to mark customer as completed:",
      error
    );

    setAiResponseError(
      error instanceof Error
        ? error.message
        : "Unable to mark the customer as completed."
    );
  }
};
  const handleClearConversation = async (): Promise<void> => {
    if (!selectedConversation) {
      return;
    }

    try {
      if (aiPollingTimerRef.current !== null) {
        window.clearInterval(aiPollingTimerRef.current);
        aiPollingTimerRef.current = null;
      }

      await clearConversationMessages(
        selectedConversation.id
      );

      setMessages([]);
      setAiResponsePending(false);
      setAiResponseError(null);
    } catch (error) {
      console.error(
        "Failed to clear conversation:",
        error
      );
    }
  };

  useEffect(() => {
  return () => {
    if (aiPollingTimerRef.current !== null) {
      window.clearInterval(aiPollingTimerRef.current);
    }
  };
}, []);

  useEffect(() => {
    async function loadCompanies() {
      try {
        setCompaniesLoading(true);
        setCompaniesError(null);

        const companyData = await getCompanies();

        setCompanies(companyData);
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Unable to load companies.";

        setCompaniesError(message);
        console.error("Failed to load companies:", error);
      } finally {
        setCompaniesLoading(false);
      }
    }

    loadCompanies();
  }, []);

  useEffect(() => {
    if (selectedCompanyId === null) {
      setCustomers([]);
    if (!preserveSelectedConversationRef.current) {
      setSelectedCustomerId(null);
      setConversations([]);
      setMessages([]);
    }
      return;
    }

    async function loadCustomers() {
      try {
        setCustomersLoading(true);
        setCustomersError(null);

        if (!preserveSelectedConversationRef.current) {
          setSelectedCustomerId(null);
          setConversations([]);
          setMessages([]);
        }

        const customerData = await getCustomers(
          selectedCompanyId as number,
          activeTab
        );

        setCustomers(customerData);
        preserveSelectedConversationRef.current = false;
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Unable to load customers.";

        setCustomers([]);
        setCustomersError(message);

        console.error("Failed to load customers:", error);
      } finally {
        setCustomersLoading(false);
      }
    }

    loadCustomers();
  }, [selectedCompanyId, activeTab]);

  useEffect(() => {
    if (selectedCustomerId === null) {
      setConversations([]);
      setMessages([]);
      return;
    }

    async function loadConversationAndMessages() {
      try {
        setConversationLoading(true);
        setMessagesLoading(true);

        setConversationError(null);
        setMessagesError(null);

        setConversations([]);
        setMessages([]);

        const conversationData = await getConversations(
          selectedCustomerId as number
        );

        setConversations(conversationData);

        if (conversationData.length === 0) {
          setMessages([]);
          return;
        }

        const selectedConversation = conversationData[0];

        const messageData = await getMessages(selectedConversation.id);

        const sortedMessages = [...messageData].sort(
          (firstMessage, secondMessage) =>
            new Date(firstMessage.createdAt).getTime() -
            new Date(secondMessage.createdAt).getTime()
        );

        setMessages(sortedMessages);
      } catch (error) {
        const message =
          error instanceof Error
            ? error.message
            : "Unable to load the conversation.";

        setConversations([]);
        setMessages([]);
        setConversationError(message);

        console.error("Failed to load conversation:", error);
      } finally {
        setConversationLoading(false);
        setMessagesLoading(false);
      }
    }

    loadConversationAndMessages();
  }, [selectedCustomerId]);

  const selectedCustomer = useMemo(() => {
    return (
      customers.find((customer) => customer.id === selectedCustomerId) ?? null
    );
  }, [customers, selectedCustomerId]);

  const selectedConversation = useMemo(() => {
    return conversations[0] ?? null;
  }, [conversations]);

  const conversationMessages = useMemo(() => {
    if (!selectedConversation) {
      return [];
    }

    return messages.filter(
      (message) => message.conversationId === selectedConversation.id
    );
  }, [messages, selectedConversation]);

 const waitForAIResponse = (
  conversationId: number,
  customerMessageId: number
): void => {
  if (aiPollingTimerRef.current !== null) {
    window.clearInterval(aiPollingTimerRef.current);
  }

  setAiResponsePending(true);
  setAiResponseError(null);

  let attempts = 0;
  const maxAttempts = 40;

  aiPollingTimerRef.current = window.setInterval(async () => {
    attempts += 1;

    try {
      const updatedMessages = await getMessages(
        conversationId
      );

      const sortedMessages = [...updatedMessages].sort(
        (firstMessage, secondMessage) =>
          new Date(firstMessage.createdAt).getTime() -
          new Date(secondMessage.createdAt).getTime()
      );

      setMessages(sortedMessages);

      const aiResponseExists = sortedMessages.some(
        (message) =>
          message.sender === "ai" &&
          message.id > customerMessageId
      );

      if (
        selectedCompanyId !== null &&
        selectedCustomerId !== null
      ) {
        const [reviewCustomers, completedCustomers] =
          await Promise.all([
            getCustomers(
              selectedCompanyId,
              "review"
            ),
            getCustomers(
              selectedCompanyId,
              "completed"
            ),
          ]);

        const isInReview = reviewCustomers.some(
          (customer) =>
            customer.id === selectedCustomerId
        );

        const isInCompleted = completedCustomers.some(
          (customer) =>
            customer.id === selectedCustomerId
        );

        /*
         * Stop once:
         * 1. An AI response exists, or
         * 2. The customer has moved to a different queue.
         */
        const customerMoved =
          (activeTab === "review" && isInCompleted) ||
          (activeTab === "completed" && isInReview);

        if (aiResponseExists || customerMoved) {
          if (aiPollingTimerRef.current !== null) {
            window.clearInterval(
              aiPollingTimerRef.current
            );

            aiPollingTimerRef.current = null;
          }

          setAiResponsePending(false);
          setAiResponseError(null);

          preserveSelectedConversationRef.current = true;

          if (isInReview) {
            setCustomers(reviewCustomers);
            setActiveTab("review");
            return;
          }

          if (isInCompleted) {
            setCustomers(completedCustomers);
            setActiveTab("completed");
            return;
          }

          return;
        }
      }

      if (attempts >= maxAttempts) {
        if (aiPollingTimerRef.current !== null) {
          window.clearInterval(
            aiPollingTimerRef.current
          );

          aiPollingTimerRef.current = null;
        }

        setAiResponsePending(false);

        setAiResponseError(
          "The AI response is taking longer than expected."
        );
      }
    } catch (error) {
      if (aiPollingTimerRef.current !== null) {
        window.clearInterval(
          aiPollingTimerRef.current
        );

        aiPollingTimerRef.current = null;
      }

      setAiResponsePending(false);

      const message =
        error instanceof Error
          ? error.message
          : "Unable to retrieve the AI response.";

      setAiResponseError(message);

      console.error(
        "Failed to retrieve AI response:",
        error
      );
    }
  }, 1500);
};

const addMessage = async (
  sender: MessageSender,
  text: string
): Promise<void> => {
  if (!selectedConversation) {
    return;
  }

  const trimmedText = text.trim();

  if (!trimmedText) {
    return;
  }

  try {
    const savedMessage = await createMessage(
      selectedConversation.id,
      sender,
      trimmedText
    );

    setMessages((currentMessages) => [
      ...currentMessages,
      savedMessage,
    ]);

    if (sender === "customer") {
      waitForAIResponse(
        selectedConversation.id,
        savedMessage.id
      );
    }
  } catch (error) {
    console.error("Failed to create message:", error);
  }
};

  const handleCompanyChange = (companyId: number | null) => {
    setSelectedCompanyId(companyId);
    setSelectedCustomerId(null);
    setCustomers([]);
    setConversations([]);
    setMessages([]);
  };

  const handleTabChange = (tab: QueueStatus) => {
    setActiveTab(tab);
    setSelectedCustomerId(null);
    setConversations([]);
    setMessages([]);
  };

  const handleCustomerSelect = (customerId: number) => {
    setSelectedCustomerId(customerId);
    setConversations([]);
    setMessages([]);
  };

  const handleCustomerMessage = (
    text: string
  ): Promise<void> => {
    return addMessage("customer", text);
  };

  const handleCompanyMessage = (
    text: string
  ): Promise<void> => {
    return addMessage("company", text);
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark">
            <FlaskConical size={20} />
          </span>

          <div>
            <h1>AI Operations Playground</h1>
            <p>Internal workflow testing environment</p>
          </div>
        </div>

        <div className="environment-badge">
          <Activity size={15} />
          Demo Environment
        </div>
      </header>

      <section className="workspace-toolbar">
        {companiesLoading && <p>Loading companies...</p>}

        {companiesError && (
          <p className="error-message">
            Failed to load companies: {companiesError}
          </p>
        )}

        {!companiesLoading && !companiesError && (
          <CompanySelector
            companies={companies}
            value={selectedCompanyId}
            onChange={handleCompanyChange}
          />
        )}
      </section>

      {customersLoading && selectedCompanyId !== null && (
        <p className="loading-message">Loading customers...</p>
      )}

      {customersError && (
        <p className="error-message">
          Failed to load customers: {customersError}
        </p>
      )}

      {conversationLoading && selectedCustomerId !== null && (
        <p className="loading-message">Loading conversation...</p>
      )}

      {messagesLoading && selectedCustomerId !== null && (
        <p className="loading-message">Loading messages...</p>
      )}

      {conversationError && (
        <p className="error-message">
          Failed to load conversation: {conversationError}
        </p>
      )}

      {messagesError && (
        <p className="error-message">
          Failed to load messages: {messagesError}
        </p>
      )}

      <div className="workspace-grid">
        <QueuePanel
          customers={customers}
          activeTab={activeTab}
          onTabChange={handleTabChange}
          selectedCustomerId={selectedCustomerId}
          onCustomerSelect={handleCustomerSelect}
          companySelected={selectedCompanyId !== null}
        />

        <ConversationWorkspace
          companySelected={selectedCompanyId !== null}
          customer={selectedCustomer}
          conversation={selectedConversation}
          messages={conversationMessages}
          onSendCustomerMessage={handleCustomerMessage}
          onSendCompanyMessage={handleCompanyMessage}
          onClearConversation={handleClearConversation}
          onMarkCompleted={handleMarkCompleted}
          showMarkCompleted={activeTab === "review"}
          aiResponsePending={aiResponsePending}
          aiResponseError={aiResponseError}
        />
      </div>
    </div>
  );
}