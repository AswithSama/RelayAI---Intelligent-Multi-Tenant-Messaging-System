# ai/buckets/all_buckets.py
from ai.buckets.after_service.buckets_registered import after_service_buckets
from ai.buckets.billing_info.buckets_registered import billing_info_buckets
from ai.buckets.needs_review.buckets_registered import needs_review_buckets
from ai.buckets.registry import BucketRegistry
from ai.buckets.upsell.buckets_registered import upsell_buckets
from ai.first_classification_layer.buckets_registered import broad_buckets

registry = BucketRegistry()

registry.register_many([
    *broad_buckets,
    *upsell_buckets,
    *after_service_buckets,
    *billing_info_buckets,
    *needs_review_buckets
])
