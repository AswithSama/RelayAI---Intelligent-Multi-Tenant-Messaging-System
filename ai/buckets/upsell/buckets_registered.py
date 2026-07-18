# ai/upsell/buckets.py

from ai.buckets.registry import BucketConfig
from ai.buckets.upsell.prompts.prompt_upsell_acceptance import upsell_acceptance
from ai.buckets.upsell.prompts.prompt_upsell_acknowledgment import upsell_acknowledgment
from ai.buckets.upsell.prompts.prompt_upsell_already_included import upsell_already_included
from ai.buckets.upsell.prompts.prompt_upsell_decline import upsell_decline
from ai.buckets.upsell.prompts.prompt_upsell_details_or_price import upsell_details_or_price
from ai.buckets.upsell.prompts.prompt_upsell_needs_review import upsell_needs_review

upsell_buckets = [

    BucketConfig(
        name="upsell_acceptance",
        prompt=upsell_acceptance,
        description="""
        Handles clean customer acceptance of an upsell/add-on offer.

        Use this bucket when:
        - The customer clearly accepts the upsell.
        - The customer wants the upsell scheduled as a new appointment.
        - The customer wants the upsell added to an existing, upcoming, or next service appointment.
        - The customer asks to schedule it, book it, add it, set it up, move forward, or have someone come out.
        - For vague positive replies like "yes", "sure", "okay", "ok", "sounds good", "go ahead", "add it", "schedule it", or "let's do it", use this bucket only when the latest assistant/company upsell message asked to add the service to the customer's next/upcoming service or asked to schedule/set up the service.

        Do NOT use this bucket when:
        - For vague positive replies when the latest assistant/company upsell message only asked whether the customer wants more information. In that case, use upsell_details_or_price.
        - The customer accepts but also asks whether the upsell is already included, already covered, already paid for, or part of their regular service. Use upsell_already_included.
        - The customer accepts but also asks about price, quote, cost, details, coverage, what is included, what the service is, how it works, or asks for more information. Use upsell_details_or_price.
        - The customer both accepts and declines, sounds contradictory, or makes the upsell intent unsafe or unclear. Use upsell_needs_review.
        - The customer is not clearly accepting the upsell.
        - The customer only sends a harmless acknowledgment with no clear acceptance. Use upsell_acknowledgment.
        - The previous assistant/company message was only confirming an action, closing the conversation, saying someone will follow up, or giving information. In that context, vague replies like "okay", "sure", "sounds good", or "got it" should use upsell_acknowledgment.

        Strict rule:
        - Use this bucket only for clean upsell acceptance with no higher-priority question, concern, contradiction, or unsafe condition, and only when the latest outbound upsell message was asking to add, schedule, set up, book, or move forward with the service.
        """,
        level="sub",
        parent="upsell",
    ),

    BucketConfig(
        name="upsell_details_or_price",
        prompt=upsell_details_or_price,
        description="""
        Handles upsell details, pricing, coverage, quote, explanation, service-detail, or safety questions.

        Use this bucket when:
        - The latest assistant/company upsell message asked whether the customer wants more information about the service, and the customer gives a short or vague positive reply.
          The latest outbound message may end with something like:
          - "Would you like more info?"
          - "Would you like more information?"
          - "Would you like more info on turf, lighting, or both?"
          In this context, replies like "yes", "sure", "yeah sure", "okay", "sounds good", "send it", "tell me more", "please let me know the details", or similar should be treated as the customer asking for more information, not as clean upsell acceptance.
        - The customer directly asks about the upsell price, quote, cost, details, coverage, what is included, how it works, what the treatment/service is, safety, preparation, ingredients/chemicals, pets, kids, timing, effectiveness, coverage area, or what happens during the service.
        - The customer shows interest in the upsell but is asking for more information before clearly committing.

        Special acceptance-with-information rule:
        - If the latest assistant/company upsell message asked to add the service to the customer's next/upcoming service, schedule the service, set it up, or move forward with it, but the customer both accepts and asks for more information in the same reply, use this bucket instead of upsell_acceptance.
        - Acceptance plus a price, details, safety, coverage, explanation, or service-related question should not be treated as clean acceptance.
        - This bucket must cover messages like:
          - "sure, how much is it?"
          - "yes, can you send me the details?"
          - "okay, what does it include?"
          - "yes, please add it, but how much will it cost?"
          - "sure, schedule it, but can you tell me what is included?"
        - Use upsell_acceptance only when the customer clearly accepts the upsell with no price, details, safety, coverage, explanation, or other upsell-related question.

        Do NOT use this bucket when:
        - The customer asks whether the upsell is already included, already covered, already paid for, or part of their regular service. Use upsell_already_included.
        - The upsell portion is only clean acceptance with no details, pricing, coverage, safety, or explanation question. Use upsell_acceptance.
        - The customer both accepts and declines, asks something unsupported, asks something unrelated to the upsell, or makes the upsell intent unsafe or unclear. Use upsell_needs_review.
        - The customer only sends a harmless acknowledgment with no question or request. Use upsell_acknowledgment.
        - The details/pricing/safety question requires customer-specific information or unsupported company policy details that cannot be safely handled by the approved upsell flow. Use upsell_needs_review.

        Strict rule:
        - If the latest message asks about upsell price, quote, details, coverage, what is included, how it works, safety, kids, pets, chemicals, preparation, timing, or any other detail about the upsell service, use this bucket unless upsell_needs_review or upsell_already_included applies.
        - If the customer accepts and asks any upsell-related question in the same latest message, this bucket has priority over upsell_acceptance.
        """,
        level="sub",
        parent="upsell",
    ),
    BucketConfig(
        name="upsell_already_included",
        prompt=upsell_already_included,
        description="""
        Handles questions about whether the upsell/add-on is already included, covered, paid for, or part of the customer's existing service.

        Use this bucket when:
        - The customer asks whether the upsell is already included or covered in their plan, regular service, subscription, agreement, treatment, or existing appointment.
        - The customer asks whether they already pay for the upsell.
        - The customer asks whether the upsell should already be covered.
        - The customer sounds confused, skeptical, mildly annoyed, or slightly frustrated, but the main upsell intent is still asking whether the upsell is already included.

        Do NOT use this bucket when:
        - The customer asks only general price, quote, details, coverage, what is included, or how it works without asking whether it is already included. Use upsell_details_or_price.
        - The customer cleanly accepts with no already-included concern. Use upsell_acceptance.
        - The customer both accepts and declines, asks something unsupported, or makes the upsell intent unsafe or unclear. Use upsell_needs_review.
        - The customer only sends a harmless acknowledgment with no already-included question. Use upsell_acknowledgment.
        - The already-included question requires unsupported customer-specific review beyond the approved upsell flow. Use upsell_needs_review.

        Strict rule:
        - If the latest message clearly asks whether the upsell is already included, covered, paid for, or part of existing service, use this bucket unless upsell_needs_review applies.
        """,
        level="sub",
        parent="upsell",
    ),

    BucketConfig(
        name="upsell_decline",
        prompt=upsell_decline,
        description="""
        Handles clean customer decline of an upsell/add-on offer.

        Use this bucket when:
        - The customer clearly says no.
        - The customer says not interested.
        - The customer says maybe later or not right now.
        - The customer asks to stop receiving the upsell offer.
        - The upsell-related part of the latest customer message is a clear refusal.

        Do NOT use this bucket when:
        - The customer both accepts and declines in the same latest message. Use upsell_needs_review.
        - The customer declines but also asks whether the upsell is already included, covered, paid for, or part of regular service. Use upsell_already_included.
        - The customer declines but also asks about price, quote, cost, details, coverage, what is included, or how it works. Use upsell_details_or_price.
        - The decline is unclear, conditional, sarcastic, hostile, or unsafe to treat as a clean refusal. Use upsell_needs_review.
        - The customer only sends a harmless acknowledgment with no clear decline. Use upsell_acknowledgment.

        Strict rule:
        - Use this bucket only for clean upsell refusal with no higher-priority question, concern, contradiction, or unsafe condition.
        """,
        level="sub",
        parent="upsell",
    ),

    BucketConfig(
        name="upsell_acknowledgment",
        prompt=upsell_acknowledgment,
        description="""
        Handles harmless acknowledgment, greeting, closing, appreciation, or non-actionable continuation replies in an upsell conversation.

        Use this bucket when:
        - The customer only says thanks, thank you, okay, ok, got it, sounds good, have a good day, or a similar closing message.
        - The customer is only acknowledging the previous message.
        - The previous assistant/company message was confirming an action, closing the conversation, saying someone will follow up, giving information, checking on something, passing something along, reviewing something, getting back to the customer, or thanking the customer.
        - The upsell-related message has no clear acceptance, no refusal, no question, no concern, and no actionable upsell intent.

        Special condition — non-actionable continuation replies:
        - Use this bucket when the previous assistant/company message already placed the conversation into a follow-up, checking, review, handoff, confirmation, or waiting state, and the latest customer message only acknowledges that state.
        - In this condition, short replies like "sure", "okay", "ok", "sounds good", "got it", "cool", "that works", "no problem", or similar should be treated as acknowledgment, not as upsell acceptance.
        - The customer is only continuing the natural conversation flow and is not making a new decision.
        - Do not repeat the same follow-up, checking, review, handoff, or confirmation response again.
        - Always classify these replies based on what the customer is replying to, not only based on the words in the latest customer message.

        Do NOT use this bucket when:
        - Do NOT use this bucket when the customer's short reply follows an assistant 'I'll check on that' message and adds no new question."
        - The previous assistant/company message clearly offered the upsell or asked whether the customer wants to move forward, and the customer replies "sure", "okay", "ok", "sounds good", "go ahead", or "let's do it". Use upsell_acceptance.
        - The customer clearly accepts the upsell. Use upsell_acceptance.
        - The customer clearly declines the upsell. Use upsell_decline.
        - The customer asks about price, quote, cost, details, coverage, what is included, or how it works. Use upsell_details_or_price.
        - The customer asks whether the upsell is already included, covered, paid for, or part of regular service. Use upsell_already_included.
        - The message is unclear, contradictory, unsupported, unsafe, angry, hostile, sarcastic, or requires human judgment. Use upsell_needs_review.
        - The acknowledgment is attached to another actionable upsell intent.

        Strict rule:
        - Use this bucket only when the latest upsell-related message is a harmless acknowledgment, greeting, closing, appreciation, or non-actionable continuation reply with no actionable meaning.
        """,
        level="sub",
        parent="upsell",
    ),

    BucketConfig(
        name="upsell_needs_review",
        prompt=upsell_needs_review,
        description="""
        Handles upsell-context messages where the upsell-related intent cannot be safely handled by any approved upsell sub-bucket.

        Use this bucket when:
        - The latest customer message is related to the upsell, but the exact upsell intent is unclear.
        - The customer message could fit multiple upsell paths in a contradictory or unsafe way.
        - The customer both accepts and declines the upsell in the same latest message.
        - The customer asks something about the upsell that cannot be answered using the approved upsell templates, available tools, or available conversation context.
        - The customer asks for customer-specific upsell, account, plan, billing, service, or appointment information that the approved upsell flow cannot safely verify.
        - The customer asks for an upsell-related action that is not supported by the approved upsell scenarios.
        - The customer is angry, hostile, sarcastic, frustrated, or upset in a way that makes automated upsell handling unsafe.
        - The message contains an upsell-related part plus another request that makes it unsafe to continue with any automated upsell action.
        - You cannot confidently choose one of the approved upsell sub-buckets: upsell_already_included, upsell_details_or_price, upsell_acceptance, upsell_decline, or upsell_acknowledgment.

        Do NOT use this bucket when:
        - The customer clearly asks whether the upsell is already included, covered, paid for, or part of regular service, and no unsafe condition exists. Use upsell_already_included.
        - The customer clearly asks about upsell price, quote, cost, details, coverage, what is included, or how it works, and no unsafe condition exists. Use upsell_details_or_price.
        - The customer clearly accepts the upsell with no unresolved question or unsafe condition. Use upsell_acceptance.
        - The customer clearly declines the upsell with no unresolved question or unsafe condition. Use upsell_decline.
        - The customer only sends a harmless acknowledgment, greeting, closing, or appreciation with no actionable meaning. Use upsell_acknowledgment.
        - The message has multiple parts, but the upsell-related part can still be safely handled by the highest-priority approved upsell sub-bucket.
        - The message is unrelated to upsell and should have been handled directly by a broader no_ai_response or handle_additional_support path instead of the upsell domain.

        Strict rule:
        - Use this bucket only when the upsell-related message cannot be safely resolved by any approved upsell sub-bucket.
        """,
        level="sub",
        parent="upsell",
    ),
]
