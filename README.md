# AI Operations Playground

A full-stack testing environment for building, observing, and validating layered AI workflows for customer conversations.

The playground allows a user to select a fictional company workspace, open a customer conversation, simulate inbound and outbound messages, and observe how an AI workflow classifies the request, selects an approved business scenario, executes controlled tools, and produces a safe response or routes the conversation for human review.

> This independent playground is inspired by production AI workflow patterns I worked on at Catapult, then rebuilt as a self-contained demonstration using fictional companies, customers, and data.

## Why This Project Exists

A production AI system should do more than send a customer message directly to an LLM and display its answer. It should control what context the model receives, separate classification from execution, restrict the model to approved actions, handle rapid message bursts, prevent stale responses, and escalate uncertain situations safely.

This project demonstrates those ideas through a layered and observable architecture rather than a single unrestricted chatbot prompt.

## Core Capabilities

- A React and TypeScript interface for testing company-specific customer conversations.
- Company workspaces with separate customers, queues, conversation histories, and business metadata.
- A FastAPI backend with PostgreSQL persistence and typed request and response models.
- A three-layer LangGraph workflow for broad routing, domain-specific classification, and final scenario selection.
- Registry-driven workflow definitions that keep prompts and supported scenarios modular.
- Structured JSON outputs with validation against approved bucket and scenario identifiers.
- A deterministic execution layer that controls tools, response templates, escalation rules, and final delivery decisions.
- A debounced background worker that combines rapid customer messages into one turn.
- Freshness checks that prevent an older AI run from responding after a newer message arrives.
- Human-review workflows for unsupported, unsafe, incomplete, or ambiguous requests.

## Application Preview

The interface is organized around three main areas.

The **Company Workspace** selector changes the business context used by the application. The **Workflow Queue** separates conversations that need review from conversations marked as completed. The **Conversation Playground** displays message history and lets a tester simulate messages from either the customer or a company representative.

When a customer message is inserted, the backend saves it, schedules an AI run, processes the conversation through the layered workflow, and stores the resulting AI message when the response is safe to send.

## System Architecture

```mermaid
flowchart LR
    UI[React Playground] --> API[FastAPI REST API]
    API --> DB[(PostgreSQL)]
    API --> Queue[Pending AI Run]
    Queue --> Worker[Debounced Background Worker]
    Worker --> L1[Layer 1: Broad Classification]
    L1 --> L2[Layer 2: Domain Classification]
    L2 --> L3[Layer 3: Scenario Selection]
    L3 --> Executor[Deterministic Executor]
    Executor --> Templates[Approved Response Templates]
    Executor --> Tools[Controlled Business Tools]
    Executor --> Escalation[Human Review]
    Templates --> DB
    Tools --> DB
    Escalation --> DB
```

## AI Workflow

### Layer 1: Broad Classification

The first layer determines which high-level workflow should handle the latest customer message. It uses the most recent conversation context to understand short replies such as “yes,” “how much,” or “sounds good,” but it is explicitly prevented from generating a customer-facing answer or calling tools.

The currently registered broad workflows are:

- `upsell`
- `after_service`
- `billing_info`
- `needs_review`

The classifier returns structured JSON, and every selected bucket is validated against the registered bucket names. Invalid or missing results fall back to the human-review workflow.

### Layer 2: Domain-Specific Classification

Only the domain agents activated by Layer 1 are executed. Each domain agent receives focused context and selects a more specific sub-bucket for the customer’s request.

This reduces prompt noise because a billing classifier does not need the full instructions for post-service feedback, and an upsell classifier does not need every billing scenario. The separation also makes each workflow easier to update, test, and reason about independently.

### Layer 3: Approved Scenario Selection

The third layer reads the selected sub-bucket prompt and chooses an approved `scenario_id`. The LLM is not allowed to invent actions, templates, prices, policies, appointment details, billing facts, or customer-specific data.

Most domains select exactly one scenario. Billing workflows can select multiple approved scenarios when a customer clearly includes multiple supported billing intents in the same message.

The selected scenario identifier is mapped in Python to a deterministic scenario output containing an approved action, response template, and required parameters.

### Deterministic Execution

The final execution layer, rather than the LLM, decides what actually happens. Depending on the approved scenario, it can:

- Format an approved customer-response template.
- Retrieve supported account or billing information.
- Forward a complaint or request to a company representative.
- Create an internal escalation for additional support.
- Produce no customer response when automation is not appropriate.

Before sending a response, the executor verifies required template variables, checks message freshness, applies stop rules, and returns an explicit status:

- `ready_to_send`
- `no_response`
- `human_attention_required`

This design keeps language understanding probabilistic while keeping business execution controlled and predictable.

## Message-Burst and Concurrency Handling

Customer messages are not processed immediately one by one. Each conversation has a single pending AI-run record, and new messages refresh that record with the latest message identifier and restart a five-second debounce window.

The worker combines all customer messages sent after the most recent company or AI response into one current customer turn. For example, three quick messages such as “Hello,” “I need help,” and “with my account” are processed together instead of generating three disconnected AI replies.

Ready jobs are claimed using PostgreSQL row locking with `FOR UPDATE SKIP LOCKED`. This supports safe worker concurrency and reduces duplicate processing. A stale running lock can be recovered after five minutes.

Freshness is checked before processing, before sensitive tool actions, and again before saving the final AI response. When a newer customer message arrives during execution, the outdated result is discarded and the conversation is scheduled again.

## Guardrails and Reliability

The project uses several complementary controls instead of relying on a single prompt:

- Layer-specific responsibilities keep classification, scenario selection, and execution separate.
- Conversation history is cleaned and limited before it is sent to classification layers.
- LLM responses use structured JSON mode.
- Bucket names and scenario identifiers are checked against approved registries.
- Customer-facing text comes from approved templates rather than unrestricted generation.
- Missing template variables block delivery and trigger human review.
- Unsupported or unsafe requests are routed to internal support.
- Tool execution is handled in Python and can be stopped when the triggering message is stale.
- Model calls use a fixed temperature, timeout, and retry policy.

The configured model is `gpt-5-mini` with temperature `0`, medium reasoning effort, a 30-second timeout, and up to two retries for transient failures.

## Technology Stack

### Frontend

- React
- TypeScript
- Vite
- Lucide React
- CSS

### Backend

- Python
- FastAPI
- Pydantic
- LangGraph
- LangChain OpenAI
- Psycopg 3

### Data and AI

- PostgreSQL
- OpenAI-compatible chat model integration
- Registry-driven prompt and workflow configuration
- Deterministic templates and tool orchestration

## Project Structure

```text
.
├── backend/
│   ├── ai/
│   │   ├── agent/                       # LangGraph state, nodes, and graph builder
│   │   ├── buckets/                     # Domain workflows, prompts, and registry entries
│   │   ├── execution_layer/             # Scenario mapping and deterministic execution
│   │   ├── first_classification_layer/  # Broad message routing
│   │   ├── shared/                      # Queue worker, freshness, model, and history utilities
│   │   ├── tools/                       # Controlled business actions
│   │   └── run_ai_workflow.py           # AI workflow entry point
│   ├── app/
│   │   ├── api/                         # FastAPI routes
│   │   ├── core/                        # Application settings
│   │   ├── database/                    # PostgreSQL connection helpers
│   │   ├── schemas/                     # Pydantic request and response models
│   │   ├── services/                    # Application and database services
│   │   └── main.py                      # FastAPI application and worker lifecycle
│   └── sql/
│       ├── schema.sql                   # Database schema
│       └── seed.sql                     # Fictional demonstration data
└── frontend/
    ├── src/
    │   ├── api/                         # Typed API client functions
    │   ├── components/                  # Workspace, queue, and conversation UI
    │   ├── data/                        # Mock data retained from earlier UI development
    │   ├── App.tsx
    │   └── styles.css
    ├── package.json
    └── vite.config.ts
```

## Database Design

The PostgreSQL schema contains the following main tables:

- `companies` stores company-specific metadata such as name, phone number, review link, and CRM type.
- `customers` belongs to a company and stores queue state, account metadata, and review information.
- `conversations` connects message histories to customers.
- `messages` stores customer, company, and AI messages.
- `ai_pending_runs` maintains one debounced background run per conversation.
- `escalation_notifications` stores human-review and representative-notification payloads.

Foreign keys use cascading deletion where appropriate, and indexes support queue filtering, conversation lookups, ordered message retrieval, pending-run claims, and escalation queries.

## REST API

All routes use the `/api/v1` prefix.

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/health` | Check backend health |
| `GET` | `/companies` | List company workspaces |
| `GET` | `/companies/{company_id}/customers` | List customers, optionally filtered by queue status |
| `GET` | `/customers/{customer_id}/conversations` | List a customer’s conversations |
| `GET` | `/conversations/{conversation_id}/messages` | Retrieve ordered conversation messages |
| `POST` | `/conversations/{conversation_id}/messages` | Insert a customer, company, or AI message |

Posting a message with `sender: "customer"` automatically creates or refreshes the pending AI run for that conversation.

Example request:

```json
{
  "sender": "customer",
  "body": "How much does the additional service cost?"
}
```

## Local Setup

### Prerequisites

Install the following tools before running the project:

- Python 3.11 or newer
- Node.js 20 or newer
- PostgreSQL 14 or newer
- An OpenAI API key

### 1. Configure PostgreSQL

Create a local database:

```bash
createdb ai_operations_playground
```

From the `backend` directory, create the schema and load the fictional seed data:

```bash
psql -d ai_operations_playground -f sql/schema.sql
psql -d ai_operations_playground -f sql/seed.sql
```

### 2. Configure the Backend

Move into the backend directory and create a virtual environment:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
```

On Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

Install the backend dependencies:

```bash
pip install fastapi "uvicorn[standard]" pydantic pydantic-settings "psycopg[binary]" langgraph langchain-core langchain-openai typing-extensions
```

Create `backend/.env`:

```env
APP_NAME=AI Operations Playground API
ENVIRONMENT=development
DEBUG=true
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ai_operations_playground
FRONTEND_URL=http://localhost:5173
OPENAI_API_KEY=your_openai_api_key
```

Do not commit `.env` files or API keys to source control.

Start the backend from the `backend` directory:

```bash
uvicorn app.main:app --reload --port 8000
```

The health endpoint should return a healthy status at:

```text
http://localhost:8000/api/v1/health
```

FastAPI documentation is available at:

```text
http://localhost:8000/docs
```

### 3. Configure the Frontend

Open a second terminal and move into the frontend directory:

```bash
cd frontend
```

If the project archive contains an existing `node_modules` directory, remove it before installation because installed packages can be operating-system specific:

```bash
rm -rf node_modules
npm install
```

Create `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Start the frontend:

```bash
npm run dev
```

Open the Vite URL shown in the terminal, normally:

```text
http://localhost:5173
```

## Using the Playground

Select a company workspace, choose either the **Needs Review** or **Completed** queue, and open a customer conversation. Existing customer, company, and AI messages will appear in chronological order.

Use **Insert customer message** to simulate an inbound message. The API stores the message and automatically schedules the AI workflow. The debounce timer waits briefly for additional customer messages before processing the combined turn.

Use **Send as company representative** to insert an outbound human response and test how later customer replies are interpreted using conversation context.

The generated AI response is saved to PostgreSQL. The current frontend does not yet poll for background results, so reselect the customer or refresh the page after processing to load the newly stored AI message.

## Extending the Workflow

A new workflow can be added by registering a broad bucket or sub-bucket, defining a focused prompt with approved scenario identifiers, mapping those identifiers in `scenario_outputs.py`, and adding any required deterministic template or tool implementation.

This approach keeps workflow expansion modular. New business cases can be introduced without turning the application into one large prompt or allowing the model to execute arbitrary behavior.

## Current Development Status

The automatic customer-message path is implemented end to end: message persistence, pending-run scheduling, debouncing, worker claiming, layered AI execution, deterministic response handling, and AI-message persistence.

The visible **Run AI** button currently calls a manual endpoint that is not implemented in the FastAPI router. The reliable execution path is the automatic run triggered when a customer message is posted. A future update can either add the manual endpoint or remove the button.

Additional production-oriented improvements would include authentication and authorization, API rate limiting, frontend polling or WebSockets, migration tooling, automated tests, structured tracing, container configuration, CI/CD, and managed worker deployment.

## Design Principles Demonstrated

This project is built around several production AI engineering principles: give each model layer only the context it needs, separate probabilistic interpretation from deterministic execution, validate every model-selected identifier, prefer approved templates for customer-facing communication, design for duplicate and stale work, and make human escalation a first-class outcome rather than an exception.
