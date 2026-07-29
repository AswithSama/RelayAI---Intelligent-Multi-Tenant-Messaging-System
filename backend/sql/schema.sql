CREATE TABLE companies (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    phone_number VARCHAR(30),
    google_review_link TEXT,
    crm VARCHAR(50),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE customers (
    id BIGSERIAL PRIMARY KEY,
    company_id BIGINT NOT NULL
        REFERENCES companies(id)
        ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    phone VARCHAR(30),
    account_number VARCHAR(100),
    queue_status VARCHAR(30) NOT NULL DEFAULT 'review',
    last_message TEXT,
    review_reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_customer_queue_status
        CHECK (queue_status IN ('review', 'completed'))
);

CREATE TABLE conversations (
    id BIGSERIAL PRIMARY KEY,
    customer_id BIGINT NOT NULL
        REFERENCES customers(id)
        ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE messages (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL
        REFERENCES conversations(id)
        ON DELETE CASCADE,
    sender VARCHAR(30) NOT NULL,
    body TEXT NOT NULL,
    requires_human_attention BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_message_sender
        CHECK (sender IN ('customer', 'company', 'ai'))
);

CREATE TABLE ai_pending_runs (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL UNIQUE
        REFERENCES conversations(id)
        ON DELETE CASCADE,
    latest_message_id BIGINT NOT NULL
        REFERENCES messages(id)
        ON DELETE CASCADE,
    run_after TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    locked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_ai_pending_run_status
        CHECK (status IN ('pending', 'running', 'completed', 'failed'))
);

CREATE TABLE escalation_notifications (
    id BIGSERIAL PRIMARY KEY,
    conversation_id BIGINT NOT NULL
        REFERENCES conversations(id)
        ON DELETE CASCADE,
    message_id BIGINT
        REFERENCES messages(id)
        ON DELETE SET NULL,
    company_id BIGINT NOT NULL
        REFERENCES companies(id)
        ON DELETE CASCADE,
    customer_id BIGINT NOT NULL
        REFERENCES customers(id)
        ON DELETE CASCADE,
    query_type VARCHAR(50) NOT NULL,
    customer_name VARCHAR(255),
    customer_phone VARCHAR(30),
    company_name VARCHAR(255),
    company_phone VARCHAR(30),
    notes TEXT,
    context TEXT,
    popup_payload JSONB NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    viewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT valid_escalation_status
        CHECK (status IN ('pending', 'viewed', 'resolved'))
);

CREATE INDEX idx_escalation_notifications_conversation
    ON escalation_notifications(conversation_id, created_at DESC);

CREATE INDEX idx_escalation_notifications_status
    ON escalation_notifications(status, created_at DESC);

CREATE INDEX idx_ai_pending_runs_status_run_after
    ON ai_pending_runs(status, run_after);

CREATE INDEX idx_customers_company_id
    ON customers(company_id);

CREATE INDEX idx_customers_company_queue
    ON customers(company_id, queue_status);

CREATE INDEX idx_conversations_customer_id
    ON conversations(customer_id);

CREATE INDEX idx_messages_conversation_created
    ON messages(conversation_id, created_at);