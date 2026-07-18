# ai/after_service/buckets.py

from ai.buckets.after_service.prompts.prompt_after_service_needs_review import after_service_review
from ai.buckets.after_service.prompts.prompt_complaints import complaints
from ai.buckets.after_service.prompts.prompt_feedback_handler import feedback_handler
from ai.buckets.registry import BucketConfig

after_service_buckets = [

    BucketConfig(
        name="after_service_complaints",
        prompt=complaints,
        description="""
        Handles after-service complaints, dissatisfaction, unresolved service issues, refund requests, and still-seeing-bugs cases that should be forwarded to the company.

        Core identity: A completed service has occurred, and the customer is now expressing dissatisfaction, reporting that the service did not work, asking for action because of the result, or saying the issue is still unresolved.

        Use this bucket when:
        - The customer reports an operational issue, mistake, or negligence by the technician during the visit, such as not locking a door/gate, leaving a mess, damaging property, entering the wrong area, or similar technician conduct complaints — even if the customer does not express strong dissatisfaction in tone.
        - The customer complains about the completed service, says they are unhappy, dissatisfied, frustrated, upset, disappointed, or says the result was bad, poor, unacceptable, not helpful, or ineffective.
        - The customer says the completed service or treatment did not work, did not help, or left an unresolved after-service issue.
        - The customer asks for a refund, cancellation, compensation, retreatment, or another visit because of the completed service.
        - The customer complains while also asking a service-related follow-up question, such as when someone can come back or whether retreatment is covered.
        - The customer says they are still seeing bugs or pests after the last service in a way that implies the service did not work, the issue is unresolved, or they want the company to take action.
        - The customer gives mixed feedback where part of the message is neutral or positive, but another part reports a completed-visit problem, unresolved pest issue, or concern.

        Do NOT use this bucket when:
        - The customer asks billing, account, payment, invoice, charge, scheduling, appointment, warranty, or coverage questions without a complaint. Use after_service_review.

        Strict rule:
        - Use this bucket when the after-service portion of the message includes a complaint, dissatisfaction, unresolved service issue, refund request, or continued pest activity that should not receive an automated customer-facing answer.
        """,
        level="sub",
        parent="after_service",
    ),

    BucketConfig(
        name="after_service_review",
        prompt=after_service_review,
        description="""
        Handles after-service questions, internal-review cases, mixed after-service messages.

        Core identity: A completed service has occurred, and the customer is now asking a non-complaint question, requesting clarification, raising a customer-specific follow-up, or asking about service details that should be reviewed before any automated answer.

        Use this bucket when:
        - The customer asks a service-related question after the completed service, including what was used, what to expect, how long it should take to work, or whether current pest activity is normal.
        - The customer asks about product, chemical, material, treatment details, or safety for pets, kids, plants, the home, or other people of a completed service
        - The customer asks about warranty, coverage, retreatment, follow-up visits, next appointment, scheduling, rescheduling, or service expectations after a completed service.
        - The customer gives positive or neutral feedback but also includes a service-related question.
        - The customer asks about billing, account, payment, invoice, charge, refund, or customer-specific account details in relation to the completed service, without clearly complaining.
        - The after-service portion of the message cannot be fully and safely resolved using the approved after-service feedback or complaint scenarios.

        Do NOT use this bucket when:
        - The customer gives positive or neutral feedback but also includes a service-related complaint/issue that customer is unhappy with.
        - The customer clearly complains, expresses dissatisfaction, reports an unresolved service issue, asks for action because the service did not work, or says they are still seeing pests in a complaint-like way → use after_service_complaints instead.
        - The after-service portion of the message is only a harmless acknowledgment, greeting, closing, or appreciation with no actionable meaning and belongs to a feedback/review-link context. Use after_service_feedback.

        Strict rule:
        - Use this bucket when the after-service portion of the message includes a question, customer-specific request, internal-review need.
        """,
        level="sub",
        parent="after_service",
    ),

    BucketConfig(
        name="after_service_feedback",
        prompt=feedback_handler,
        description="""
        Handles clean positive feedback, neutral feedback, and Google review-link replies in an after-service conversation.

        Core identity: A completed service has occurred, and the customer is only giving simple feedback or replying to a review/feedback request without asking a service question, making a complaint, or requesting customer-specific action.

        Use this bucket when:
        - The customer gives clear positive feedback about the completed service, such as good, great, excellent, helpful, amazing, perfect, or clearly positive.
        - The customer gives neutral feedback such as fine, okay, ok, not bad, it was fine, all good, or a similar neutral response.
        - The previous company message asked for a review or sent a review link, and the customer agrees to leave a review, says they already completed it, declines, or says they cannot leave one.
        - The customer only sends a harmless acknowledgment, greeting, closing, or appreciation in a feedback/review-link context.

        Do NOT use this bucket when:
        - The customer gives positive or neutral feedback but also asks a service question, billing, scheduling, warranty, coverage question, or customer-specific request → use after_service_review instead.
        - The customer complains, expresses dissatisfaction, reports an unresolved issue, asks for refund/retreatment/company action because of the completed service, or says the service did not work → use after_service_complaints instead.

        Multi-intent:
        - Do not use this bucket if the after-service portion of the message contains any actionable question, complaint, customer-specific request, or internal-review need.
        - If clean feedback is combined with any service, billing, scheduling, warranty, coverage, or treatment-result question after completed service, use after_service_review instead.

        Strict rule:
        - Use this bucket only when the after-service portion of the message is clean after-service feedback, neutral feedback, a review-link reply, or a harmless acknowledgment with no complaint, unresolved issue, service question, or customer-specific request.
        """,
        level="sub",
        parent="after_service",
    ),
]
