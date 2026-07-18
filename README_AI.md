# `ai/` — Inbound-reply LLM subsystem

> Generates (and optionally sends) replies to inbound customer SMS via a layered LangGraph pipeline. Read the root `../CLAUDE.md` first for system-wide context. (`README_AI.md` in this folder is currently empty — this file replaces it.)

## Entry point & how it's invoked

- **`run_ai_workflow.py`** — the public surface:
  - `ai_workflow(customer_id, company_id, body, message_id=None) -> str | None` — returns just the customer-facing reply text (or `None`).
  - `ai_workflow_with_meta(...) -> dict` — full envelope (buckets chosen, execution plan, tool results, template key, `response_status`).
- **Callers:** `services/webhooks.py` (`enqueue_ai_pending_run`), `main.py` (`ai_pending_run_loop`), `api/dev_tools.py` (`run_ai_workflow_for_pending_message`, used by the dev AI Playground).

**Live dispatch path (production):** inbound webhook → `enqueue_ai_pending_run()` writes/updates the `ai_pending_runs` table (`ON CONFLICT (company_id, customer_id) DO UPDATE`, so rapid messages from one customer **debounce** into a single run — `40s` prod / `10s` non-prod) → the **in-process** `ai_pending_run_loop()` started in `main.py` polls (~3s), claims a ready run, calls `run_ai_workflow_for_pending_message()` → `ai_workflow_with_meta()` → sends via `services.messaging.send_message_core()`. An `is_still_latest_inbound()` check skips stale runs. **There is no Cloud Tasks `ai-inbound-replies` queue live in prod** — this DB-polling loop is the real path (an earlier Cloud Tasks + `catapult-ai-worker` design was reverted 2026-06-06).

## The graph (4 sequential nodes)

Compiled `StateGraph` in `agent/graph_builder.py`; shared `AgentState` TypedDict in `agent/state.py`.

```
START
 1. load_conversation_history   (agent/graph_nodes.py)
      → customer first name, company data, last-24h history, review link, company phone
 2. classify_broad_buckets      Layer 1  (first_classification_layer/broad_classifier_agent.py)
      → 1–N of: upsell | after_service | billing_info | needs_review
 3. run_activated_domain_agents Layer 2  (buckets/<bucket>/…)
      → per active bucket, pick a sub-bucket (upsell ~6, after_service, billing may be multiple)
 4. layer3_scenario_selector    Layer 3  (execution_layer/layer3_agent.py)
      → LLM picks an approved scenario_id, mapped via execution_layer/scenario_outputs.py
        (SCENARIO_OUTPUTS) to {action, template_key, parameters}, then
        execution_layer/deterministic_executor_node.py runs tools + formats the approved template
END
```

**`response_status`** (on the result): `ready_to_send` (safe to text), `no_response` (nothing selected), `human_attention_required` (escalated / missing template vars).

## Directory map

- `agent/` — `state.py` (AgentState), `graph_builder.py` (compiles the graph), `graph_nodes.py` (node fns incl. history load).
- `first_classification_layer/` — Layer-1 broad classifier + `prompts/`.
- `buckets/` — domain (Layer-2) agents + registry. One folder per broad bucket: `upsell/`, `after_service/`, `billing_info/`, `needs_review/`, each with a `prompts/` subfolder. `registry.py` / `all_buckets_registered.py` wire them up.
- `execution_layer/` — `layer3_agent.py` (scenario selection), `scenario_outputs.py` (`SCENARIO_OUTPUTS` map + template registry), `deterministic_executor_node.py` (tool execution + template formatting; the final node).
- `tools/` — the actions the executor can invoke (below).
- `shared/` — `pending_runs.py` (enqueue/debounce), `pending_run_worker.py` (run one ready message), `pending_run_loop.py` (the background poller), `model.py` (OpenAI client via langchain — confirm the exact model here, currently `gpt-4o-mini`), `clean_message_history.py`.
- `utils/` — small helpers (e.g. day-of-week for templates).
- `prompts/` — **empty**; real prompts live under each bucket's `prompts/`. Each prompt is a function `prompt_*(state) -> str`.

## Tools (`tools/`)

- **`forward_message_to_company`** (`tool_forward_message.py`) — escalate to the office (complaint/billing/scheduling/overdue_service/service_info/upsell_*). Marks the inbound message `account_manager_dismissed_at = NOW()`, `requires_human_attention = FALSE`, and writes an escalation. **Dry-run unless `ENVIRONMENT == "prod"`** (logs "would send").
- **`handle_additional_support`** (`tool_additional_support.py`) — flag the conversation for a human: sets `requires_human_attention = TRUE` (surfaces in Message Center's Account-manager tab until an operator takes it).
- **`get_customer_account_info`** (`tool_billing_info.py`) — normalized billing/account lookup from the CRM (FieldRoutes/GorillaDesk); cached on `state["account_info"]`.

## Invariants — do NOT break

- **Env gating:** off-prod, the forward/send tools dry-run; debounce is `40s` prod / `10s` non-prod. Keep both behaviors.
- **Idempotency / debounce** rests on the `ai_pending_runs` upsert keyed by `(company_id, customer_id)` plus `is_still_latest_inbound()`. Don't replace the upsert with plain inserts.
- **Stop rules:** a complaint forward or `handle_additional_support` short-circuits the rest (status → `human_attention_required`); a template missing variables triggers `handle_additional_support` rather than texting a broken template. Preserve these guards.
- **Side-effect writes:** upsell opt-ins and forwards write `recent_activity_events`. Templates only send when `response_status == ready_to_send`.
