INSERT INTO companies (id, name)
VALUES
    (1, 'Northstar Home Services'),
    (2, 'BlueSky Pest Control'),
    (3, 'Evergreen Property Care');

INSERT INTO customers (
    id,
    company_id,
    name,
    phone,
    queue_status,
    last_message
)
VALUES
    (
        1,
        1,
        'John Smith',
        '+13125550101',
        'review',
        'Can you tell me more about the service?'
    ),
    (
        2,
        1,
        'Emily Johnson',
        '+13125550102',
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