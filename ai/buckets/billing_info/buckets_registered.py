# ai/billing_info/buckets.py

from ai.buckets.billing_info.prompts.prompt_autopay_expired import billing_autopay_info
from ai.buckets.billing_info.prompts.prompt_billing_account_info import billing_account_info
from ai.buckets.billing_info.prompts.prompt_billing_needs_review import billing_needs_review
from ai.buckets.billing_info.prompts.prompt_billing_overdue_ar import billing_overdue_ar
from ai.buckets.registry import BucketConfig

billing_info_buckets = [
    BucketConfig(
        name="billing_account_info",
        prompt=billing_account_info,
        description="""
        Handles approved direct-response account-access cases.

        Core identity: The customer is asking how to access their own account, including account number, login, portal access, or password reset.

        Use this bucket when:
        - The customer asks how to log in, access their account, or access the customer portal.
        - The customer says they cannot log in or need help accessing their account.
        - The customer asks for their account number, password help, forgot-password help, or password reset.
        - The customer asks for both account number and login/password help in the same message.

        Do NOT use this bucket when:
        - The customer asks why they were charged, what a balance is for, or asks about invoices, refunds, payment history, disputed charges, failed payments, discounts, account status, or other customer-specific billing details → use billing_needs_review unless it matches an approved AR/reminder scenario.
        - The customer is replying to an autopay, card-update, AR/payment-reminder, or overdue-service prompt → use the matching billing sub-bucket.
        - The billing/account/payment portion of the message is unclear, mixed, unsupported, or requires human review → use billing_needs_review.

        Strict rule:
        - Use this bucket only when the billing/account/payment portion of the message can be safely handled by an approved account-number, login, portal-access, or password-reset template.
        """,
        level="sub",
        parent="billing_info",
    ),
    BucketConfig(
        name="billing_autopay_info",
        prompt=billing_autopay_info,
        description="""
        Use this sub-bucket only when the latest customer message is either:
        - A direct acknowledgment/status reply to the autopay or expired card-update request, such as yes, no, not now, maybe later, cannot do it yet, will do it, done, updated it, or already did it.
        - A direct question asking why autopay is needed or why the expiring card/card update is needed.

        Do NOT use this bucket when:
        - The message includes any additional billing/account/payment question beyond the approved autopay/expired card-update acknowledgment or “why” question.
        - The customer asks how to set up autopay or how to update a card.
        - The customer asks the company to enable autopay, update payment details, run a payment, confirm a payment, or process anything.
        - The customer asks about charges, balances, invoices, refunds, payment history, failed payments, account details, or any other billing/payment issue.

        Examples:
        - "Yeah, we'll do it now." -> billing_autopay_info
        Reason: This is a clean acknowledgment/status reply. The customer is only saying they will complete the autopay or card-update request.

        - "No thanks." -> billing_autopay_info
        Reason: This is a clean decline/refusal of the autopay or card-update request.

        - "Sure." -> billing_autopay_info
        Reason: This is a short acknowledgment/agreement. If the previous company message clearly asked for autopay setup or card update, this clean reply can be handled by billing_autopay_info.

        - "Why do I need to do that?" -> billing_autopay_info
        Reason: This is a direct “why” question about the previous autopay/card-update request. This bucket only allows direct questions asking why autopay is needed or why the expiring card/card update is needed.

        - "Sure, can you check whether I have done it or not?" -> billing_needs_review
        Reason: Although the message starts with a clean acknowledgment, the customer also asks the company to check their account/status. That is an account-specific follow-up question. billing_autopay_info does not verify account status, check whether an update was completed, or answer follow-up questions, even if the follow-up is small.

        - "I have just done it. Can you see it?" -> billing_needs_review
        Reason: Although the customer says they completed the card update/autopay action, they also asks the company to confirm or verify it. That requires checking account/payment status. billing_autopay_info only handles clean completion confirmations, not verification questions.

        - "I have just done it. Can you check it?" -> billing_needs_review
        Reason: The customer is not only confirming completion; they are asking the company to check or validate the update. Any request to check, confirm, verify, or review account/payment status must go to billing_needs_review.

        Strict rule:
        Important distinction:
        - Clean acknowledgment only -> billing_autopay_info.
        - Clean question asking why autopay is needed or why the expiring card/card update is needed -> billing_autopay_info.
        - Acknowledgment with/without any follow-up question/request -> billing_needs_review.
        - Even small follow-up questions like "can you check?", "can you see it?", "did it go through?", or "am I good now?" require account/status verification, so they must be routed to billing_needs_review.
        """,
        level="sub",
        parent="billing_info",
    ),

    BucketConfig(
        name="billing_overdue_ar",
        prompt=billing_overdue_ar,
        description="""
            Use this sub-bucket only when the latest customer message is either:
            - An approved reply to a previous AR/overdue payment-reminder message, such as will pay now, will pay later, no longer uses the company, does not understand why they owe, already paid, or thought they were on autodraft.
            - An approved reply to a previous overdue-service/missed-service scheduling message, such as declining the overdue service or providing scheduling availability.

            Do NOT use this bucket when:
            - The message includes any additional billing/account/payment/scheduling question beyond the approved AR or overdue-service reply meanings.
            - The customer asks for invoice details, charge details, refund details, failed payment details, payment history, discounts, account status, a billing dispute, payment instructions, or card/autopay updates.
            - The customer asks about normal scheduling that is not clearly tied to a previous overdue-service or missed-service scheduling message.
            - The customer replies to an autopay setup request or expiring-card/card-update request.

            Strict rule:
            - Clean approved AR reply only -> billing_overdue_ar.
            - Clean approved overdue-service reply only -> billing_overdue_ar.
            - Approved “I do not understand why I owe” question/objection only -> billing_overdue_ar.
            - Approved reply plus any follow-up question/request -> billing_needs_review.
            - Any billing/account/payment/scheduling question outside the approved meanings -> billing_needs_review.
            """,

        level="sub",
        parent="billing_info",
    ),

    BucketConfig(
        name="billing_needs_review",
        prompt=billing_needs_review,
        description="""
        Handles billing/account/payment/overdue-service messages that require internal review, do not fit the other billing sub-buckets, or should not receive another automated reply.

        Core identity: The customer message is related to billing, account, payment, autopay, card updates, AR/payment reminders, or overdue service, but it does not cleanly fit billing_account_info, billing_autopay_info, or billing_overdue_ar. This bucket also handles non-actionable follow-up acknowledgments where sending another automated reply would be unnecessary.

        Use this bucket when:
        - The latest customer message is billing/account/payment-related but cannot be confidently classified into billing_account_info, billing_autopay_info, or billing_overdue_ar.
        - The customer asks for customer-specific billing details, payment details, invoice details, refund details, charge details, account status, balance explanation, disputed billing, failed payment details, discounts, or payment history.
        - The customer asks how to set up autopay, asks for autopay setup instructions, asks how to update a card, asks for card-update instructions, asks for payment instructions, or asks the company to update payment details for them.
        - The customer corrects, disputes, challenges, or complains about a billing/account/payment answer in a way that requires internal review.
        - The billing/account/payment portion of the message is unclear, mixed, unsupported, contradictory, sensitive, or requires human judgment before responding.
        - The customer sends only an acknowledgment, closing, or non-actionable follow-up that does not fit billing_account_info, billing_autopay_info, or billing_overdue_ar, especially when the system/company has already responded and another automated reply would create a duplicate or unnecessary acknowledgment.

        Do NOT use this bucket when:
        - The customer is replying to an autopay or expiring-card message with a supported reply type: why is this needed, no/refusal, will-do, already-done, or cannot-do-yet → use billing_autopay_info.
        - The customer is replying to an AR/payment-reminder message or overdue-service scheduling message with a supported AR/overdue-service reply → use billing_overdue_ar.
        - The billing/account/payment portion of the message can be fully and safely handled by billing_account_info, billing_autopay_info, or billing_overdue_ar.
        - The customer is replying to a message about scheduling or rescheduling a service that has not yet been completed, and the customer either declines the service or provides scheduling availability. This includes messages like overdue service, missed service, service rescheduling, service back on the calendar, service back on the schedule, due for service, or next route → use billing_overdue_ar.
        - Do not route a message here only because it is an acknowledgment. First check whether the acknowledgment clearly fits billing_account_info, billing_autopay_info, or billing_overdue_ar. Use this bucket only when the acknowledgment does not fit those sub-buckets, or when the system/company has already acknowledged the customer and another reply would create a duplicate or unnecessary acknowledgment.

        Exception — AR/reminder charge or balance questions:
        - If the customer is replying to an AR/payment-reminder message and asks why they owe, what the balance is for, why they received the reminder, or why they were charged in that reminder context → use billing_overdue_ar.
        - Use billing_needs_review only when the charge, invoice, refund, payment-history, dispute, or balance question is outside the supported AR/payment-reminder cases.

        Strict rule:
        - Use this bucket whenever the billing/account/payment portion of the message cannot be safely resolved by billing_account_info, billing_autopay_info, or billing_overdue_ar, or when the message is only a non-actionable follow-up acknowledgment that should not receive another automated reply.
        """,
        level="sub",
        parent="billing_info",
    ),
]
