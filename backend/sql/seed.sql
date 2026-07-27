INSERT INTO companies (
    id,
    name,
    phone_number,
    google_review_link,
    crm
)
VALUES
    (
        1,
        'Northstar Home Services',
        '+13125551001',
        'https://example.com/reviews/northstar',
        'fieldroutes'
    ),
    (
        2,
        'BlueSky Pest Control',
        '+13125551002',
        'https://example.com/reviews/bluesky',
        'gorilladesk'
    ),
    (
        3,
        'Evergreen Property Care',
        '+13125551003',
        'https://example.com/reviews/evergreen',
        'pestpac'
    );

INSERT INTO customers (
    id,
    company_id,
    name,
    phone,
    account_number,
    queue_status,
    last_message
)
VALUES
    (
        1,
        1,
        'John Smith',
        '+13125550101',
        'NS-10001',
        'review',
        'Can you tell me more about the service?'
    ),
    (
        2,
        1,
        'Emily Johnson',
        '+13125550102',
        'NS-10002',
        'completed',
        'Thank you'
    );

INSERT INTO conversations (id, customer_id)
VALUES
    (1, 1),
    (2, 2);

INSERT INTO messages (
    conversation_id,
    sender,
    body
)
VALUES
    (
        1,
        'customer',
        'Can you tell me more about the service?'
    ),
    (
        1,
        'company',
        'Of course. What information would you like?'
    );