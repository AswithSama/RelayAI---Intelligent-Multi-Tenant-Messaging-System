# ai/buckets/buckets.py

"""Registers broad bucket configurations."""

from ai.buckets.registry import BucketConfig

broad_buckets = [
    BucketConfig(
        name="upsell",
        description="""
        Handles customer replies to an active upsell or add-on offer.

        Core identity: The company has offered a NEW or OPTIONAL service the customer does not yet have. The customer is now responding to that offer.

        Use this bucket when:
        - The previous company message offered an upgrade, add-on, extra treatment, or optional service the customer has not yet received.
        - The customer accepts, declines, hesitates, or asks about the offered add-on(price, details, coverage, scheduling, whether it can be added).
        - The customer gives a short vague reply (yes, sure, no, how much, add it, sounds good) and context confirms they are responding to that offer.

        Do NOT use this bucket when:
        - The message is not clearly tied to an active upsell/add-on offer.
        - The customer is giving feedback or asking questions about a service already completed → use after_service instead.
        - The customer asks a billing, payment, autopay, or account question unrelated to the offered add-on → use billing_info instead.
        - Any part of the message cannot be safely handled by a supported bucket → use needs_review instead.

        Multi-intent:
        - Can be combined with another broad bucket if the upsell reply is one clear part and every other part is also safely handled by a supported bucket.
        - If any other part is unsupported, unclear, or requires human review → use needs_review instead.
        """,
        level="broad",
    ),
    BucketConfig(
        name="after_service",
        description="""
        Handles customer replies after a completed pest-control service, after-service follow-up, or review request.

        Use this bucket when:
        - The previous assistant/company message asked how the service went, requested feedback, asked for a review, or sent a review link.
        - The customer is talking about the result of a completed treatment or service visit.
        - The customer says the service was good, fine, okay, helpful, bad, disappointing, not effective, or did not resolve the issue.
        - The customer replies to a review request or review link with yes, no, done, cannot log in, does not use Google, or cannot leave a review.
        - The customer reports still seeing bugs or pests after treatment.
        - The customer asks what was used, whether the treatment is safe, whether pest activity is normal, whether retreatment is needed, or when the treatment should take effect.
        - The customer complains about a completed service or says the issue was not resolved.

        Do NOT use this bucket when:
        - The latest customer message is clearly replying to an upsell/add-on offer. Use upsell instead.
        - The customer asks about pricing, details, coverage, scheduling, adding, or including an offered add-on. Use upsell instead when the latest message is responding to an upsell offer.
        - The customer asks a normal billing, account, payment, invoice, autopay, card, login, or account-number question unrelated to after-service feedback. Use billing_info instead.
        - The customer asks a normal service/scheduling question that is not connected to a completed service or after-service follow-up, if another supported bucket exists for that.
        - Any part of the latest customer message cannot be safely handled by a supported broad bucket. Use needs_review instead.

        Multi-intent handling:
        - Do not use this bucket only because the message mentions service in a general way.
        - Use this bucket when the after-service feedback, completed-service result, review-link reply, or post-treatment question is one clear part of the latest customer message and every other part can also be safely handled by supported broad buckets.
        - If the message contains after-service feedback plus another safe supported intent, this bucket can be selected along with the other relevant broad bucket.
        - If the message contains after-service feedback plus an unsupported, unsafe, unclear, or human-review-required part, use needs_review instead.

        Strict rule:
        - Use this bucket only when the latest customer message is connected to a completed service, post-service feedback, treatment result, or review request.
        - If the latest message is about an offered add-on rather than completed-service feedback, do not use this bucket.
        """,
        level="broad",
    ),
    BucketConfig(
        name="billing_info",
        description="""
        Handles customer messages about their own account, billing, payment status, autopay/card updates, AR reminders, and overdue-service prompts.

        Core identity:
        This bucket is for account/payment workflows only: account access, account number, login/password help, autopay setup, expiring-card updates, AR/payment reminders, overdue balances, payment-status corrections, and overdue-service prompt replies.

        Use this bucket when:
        - The customer asks how to log in, asks for portal access, asks for their account number, or asks about password reset/help.
        - The customer asks why autopay is needed, why they need to update an expiring card, or why they received an autopay/card-update message.
        - The customer replies to an autopay or expiring-card request by saying yes, no, they will do it now, already did it, cannot do it yet, do not have the new card yet, or are waiting for the card.
        - The customer replies to an AR/payment reminder, overdue balance, autodraft, or account-receivable message about money owed by saying they will pay now, will pay later, need more time, already paid, thought autodraft/autopay handled it, no longer use the company, cancelled, do not owe it, or do not understand why they owe.
        - The customer replies to an overdue-service, missed-service, or service-back-on-schedule prompt by declining the service, refusing to schedule, saying they do not want it, saying they are not interested, or providing available times/dates/days for the overdue service.

        Do NOT use this bucket when:
        - The customer asks about price, cost, details, payment, billing, or inclusion for an upsell/add-on offer. Use upsell.
        - The customer asks about a charge, payment, or invoice only because of a completed pest-control visit, post-service complaint, treatment result, or completed-service follow-up. Use after_service.
        - The customer asks to schedule, reschedule, confirm, cancel, or change a normal service appointment, unless they are replying to an overdue-service prompt.
        - The message is unsupported, unclear, unrelated, or requires human review outside the supported billing/account workflows.

        Multi-intent:
        - Can be combined with another broad bucket only when the billing/account intent is clearly separate and every other part is safely handled by a supported bucket.
        - If any other part is unsupported, unclear, or requires human review, use needs_review instead.
        """,
        level="broad",
    ),
    BucketConfig(
        name="needs_review",
        description="""
        Catches messages that cannot be fully and safely handled by any supported bucket.

        Use this bucket when:
        - Any part of the latest message cannot be clearly mapped to a supported bucket.
        - The message requires human judgment before any automated response or action.
        - The customer is clearly hostile, threatening, profane, abusive, or emotionally escalated in a way that makes automated handling unsafe. Use needs_review.
        - The customer disputes, corrects, contradicts, or challenges a previous AI/company response, especially when they say the prior answer was wrong, inaccurate, misunderstood them, used the wrong context, selected the wrong service, or failed to address their actual issue. Use needs_review.

        Do NOT use this bucket when:
        - Every part of the message can be safely handled by one or more supported buckets.
        - The customer sounds mildly irritated, blunt, or uses pushback but the message still clearly fits a supported bucket (e.g. "Isn't this included?", "Why am I being charged?", "This still isn't fixed" → route by topic, not tone).
        - The complaint is about after-service results or unresolved pests → use after_service unless tone is clearly hostile or threatening.

        Frustration threshold:
        - Do not use needs_review only because the customer sounds mildly annoyed, impatient, blunt, skeptical, or asks a difficult question. Route those messages to the correct supported bucket.
        - Use needs_review when the customer uses profanity, personal attacks, threats, abusive language, repeated aggressive messages, or strong emotional escalation that requires human judgment.

        Multi-intent:
        - If every part of the message is handled by supported buckets, select those buckets instead.
        - If even one part is unsupported, unsafe, or unclear → use needs_review.
        """,
        level="broad",
    ),
]
