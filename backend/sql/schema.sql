CREATE TABLE companies (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,

    -- Used by billing/password-related templates
    phone_number VARCHAR(30),

    -- Used by after-service review templates
    google_review_link TEXT,

    -- Lets the playground mimic CRM-specific behavior
    -- Examples: fieldroutes, gorilladesk, pestpac
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

    -- Mocked account number used by billing/account-info templates
    account_number VARCHAR(100),

    queue_status VARCHAR(30) NOT NULL DEFAULT 'review',

    last_message TEXT,

    -- Used when AI decides human review is required
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

    -- Allows the playground to reproduce AI escalation behavior
    requires_human_attention BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT valid_message_sender
        CHECK (sender IN ('customer', 'company', 'ai'))
);


CREATE INDEX idx_customers_company_id
    ON customers(company_id);


CREATE INDEX idx_customers_company_queue
    ON customers(company_id, queue_status);


CREATE INDEX idx_conversations_customer_id
    ON conversations(customer_id);


CREATE INDEX idx_messages_conversation_created
    ON messages(conversation_id, created_at);