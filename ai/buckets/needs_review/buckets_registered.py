from ai.buckets.needs_review.prompts.prompt_needs_review import needs_review
from ai.buckets.registry import BucketConfig

needs_review_buckets = [
    BucketConfig(
        name="needs_review_general",
        prompt=needs_review,
        description="""
        Handles messages routed to needs_review by Layer 1.

        This sub-bucket exists to keep the workflow shape consistent across all domains.
        It does not require an LLM prompt because Layer 1 already determined the message requires internal representative review.

        Use this bucket when:
        - The parent bucket is needs_review.

        Strict rule:
        - Route directly to internal review handling.
        """,
        level="sub",
        parent="needs_review",
    ),
]
