"""
ai/agent/graph_builder.py

Builds the layered AI workflow graph.
"""

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph

from ai.agent.graph_nodes import load_conversation_history_node
from ai.agent.state import AgentState
from ai.buckets.after_service.after_service_agent import classify_after_service_sub_bucket
from ai.buckets.billing_info.billing_agent import classify_billing_sub_buckets
from ai.buckets.needs_review.needs_review_agent import classify_needs_review_sub_bucket
from ai.buckets.registry import BucketRegistry
from ai.buckets.upsell.upsell_agent import classify_upsell_sub_bucket
from ai.execution_layer.layer3_agent import layer3_scenario_selector_node
from ai.first_classification_layer.broad_classifier_agent import classify_broad_buckets_node


def run_activated_domain_agents_node(registry: BucketRegistry):
    def node(state: AgentState) -> Dict[str, Any]:
        broad_bucket_results = state.get("broad_bucket_results", [])
        latest_customer_message = state.get("customer_message") or ""

        domain_results = []
        active_domain_buckets = []

        for broad_result in broad_bucket_results:
            broad_bucket = broad_result.get("bucket")

            if not broad_bucket:
                continue

            if broad_bucket == "upsell":
                upsell_result = classify_upsell_sub_bucket(
                    registry=registry,
                    state=state,
                )

                domain_results.append(upsell_result)

                sub_bucket = upsell_result.get("sub_bucket")
                if sub_bucket and sub_bucket not in active_domain_buckets:
                    active_domain_buckets.append(sub_bucket)

                continue

            if broad_bucket == "after_service":
                after_service_result = classify_after_service_sub_bucket(
                    registry=registry,
                    state=state,
                )

                domain_results.append(after_service_result)

                sub_bucket = after_service_result.get("sub_bucket")
                if sub_bucket and sub_bucket not in active_domain_buckets:
                    active_domain_buckets.append(sub_bucket)

                continue

            if broad_bucket == "billing_info":
                billing_result = classify_billing_sub_buckets(
                    registry=registry,
                    state=state,
                )

                billing_domain_results = billing_result.get("domain_results", [])

                for billing_domain_result in billing_domain_results:
                    domain_results.append(billing_domain_result)

                    sub_bucket = billing_domain_result.get("sub_bucket")
                    if sub_bucket and sub_bucket not in active_domain_buckets:
                        active_domain_buckets.append(sub_bucket)

                continue

            if broad_bucket == "needs_review":
                needs_review_result = classify_needs_review_sub_bucket(
                    state=state,
                )

                domain_results.append(needs_review_result)

                sub_bucket = needs_review_result.get("sub_bucket")
                if sub_bucket and sub_bucket not in active_domain_buckets:
                    active_domain_buckets.append(sub_bucket)

                continue

            domain_results.append(
                {
                    "domain": broad_bucket,
                    "sub_bucket": broad_bucket,
                    "customer_message": latest_customer_message,
                    "reason": broad_result.get("reason", ""),
                }
            )

            if broad_bucket not in active_domain_buckets:
                active_domain_buckets.append(broad_bucket)

        return {
            "domain_results": domain_results,
            "active_domain_buckets": active_domain_buckets,
        }

    return node


def create_graph(bucket_registry: BucketRegistry):
    graph = StateGraph(AgentState)

    graph.add_node("load_conversation_history", load_conversation_history_node)
    graph.add_node("classify_broad_buckets", classify_broad_buckets_node(bucket_registry))
    graph.add_node("run_activated_domain_agents", run_activated_domain_agents_node(bucket_registry))
    graph.add_node("layer3_scenario_selector", layer3_scenario_selector_node(bucket_registry))

    graph.add_edge(START, "load_conversation_history")
    graph.add_edge("load_conversation_history", "classify_broad_buckets")
    graph.add_edge("classify_broad_buckets", "run_activated_domain_agents")
    graph.add_edge("run_activated_domain_agents", "layer3_scenario_selector")
    graph.add_edge("layer3_scenario_selector", END)

    return graph.compile()
