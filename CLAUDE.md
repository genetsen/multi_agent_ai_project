# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a modular, multi-agent AI system for harmonizing, classifying, validating, and tracking media and analytics data. The system is designed around composability: each agent consumes a well-defined input contract and produces a well-defined output contract with confidence scores, provenance, and logs.

## Architecture

### Agent Pipeline Flow

The system is structured as a pipeline where agents pass data to each other:

```
┌─────────────┐     ┌─────────────────┐     ┌─────────────────┐     ┌─────────────┐     ┌────────────────┐
│   Email     │────▶│ Data            │────▶│ Classification  │────▶│     QA      │────▶│   Dashboard    │
│   Scanner   │     │ Harmonization   │     │     Agent       │     │    Agent    │     │   Validation   │
└─────────────┘     └─────────────────┘     └─────────────────┘     └─────────────┘     └────────────────┘
      │                     │                       │                      │
      ▼                     ▼                       ▼                      ▼
 [review_queue]        [run_log]            [exceptions_queue]       [qa_results]
```

**0. Email Scanner Agent** → Monitors email for first-party data deliveries
   - Scans: Email inboxes (Gmail, Outlook, IMAP)
   - Extracts: Attachments, links (Google Sheets, Dropbox, etc.), inline tables
   - Outputs: `auto_process_payloads[]` (routed to Data Harmonization), `review_queue[]`
   - See: `agents/email_scanner/AGENT_DESIGN.md` for full technical design

**1. Data Harmonization Agent** → Ingests heterogeneous first-party data and normalizes it to canonical schema
   - Outputs: `harmonized_table`, `schema_map`, `run_log`
   - See: `agents/data_harmonization/AGENT_DESIGN.md` for full technical design

**2. Classification Agent** → Maps partner naming conventions to internal taxonomy
   - Consumes: `harmonized_table` from Data Harmonization Agent
   - Outputs: `classified_table` (adds internal IDs, channel, format, match metadata), `exceptions_queue`

**3. Quality Assurance Agent** → Validates integrity, completeness, and schema compliance
   - Consumes: `classified_table` from Classification Agent
   - Outputs: `qa_results`, `qa_summary`

**4. Dashboard Validation Agent** → Compares dashboard metrics against validated model tables
   - Consumes: `qa_passed_tables` from QA Agent
   - Outputs: `validation_report`, `trust_score`

**5. Project Tracker Agent** → Extracts decisions, action items, and blockers from communications
   - Consumes: `messages[]` from email/Slack/meetings
   - Outputs: `project_state`, `narrative`, `followups`

### Contract System

All agent contracts are defined in `schemas/contracts/`. Each agent has:
- Input contract specifying required/optional fields
- Output contract guaranteeing structured outputs
- Common conventions inherited from `schemas/contracts/COMMON_CONVENTIONS.md`

**Required fields across all contracts:**
- `run_id` - unique identifier for the agent run
- `input_provenance` - source tracking (file, table, message IDs, timestamps)
- `schema_version` - semantic version for contract payload
- `confidence` - 0–1 confidence score for key decisions
- `explanations` - structured rationale for decisions
- `errors` / `warnings` - machine-readable error/warning lists

**Data lineage requirements:**
Every row-level output must be traceable to source via:
- `source_system`
- `source_location` (URL/path/table)
- `source_record_id` (if available)
- `ingested_at`

### Core Principles

- **Explainability first** - All decisions must include explanations
- **Confidence scoring everywhere** - Use 0-1 scores for uncertain decisions
- **Human-in-the-loop by default** - Create exception queues for review
- **No silent assumptions** - Flag ambiguities explicitly
- **Composable and testable agents** - Each agent is independently testable

## Key Files and Locations

- `docs/project/project_plan.md` - System design and agent descriptions
- `ROADMAP.md` - Phased development plan
- `schemas/contracts/` - Agent input/output contracts
- `schemas/contracts/COMMON_CONVENTIONS.md` - Shared contract conventions
- `schemas/examples/` - Example input payloads for each agent
- `agents/*/README.md` - Individual agent documentation

## Development Workflow

### Working with Agents

Each agent directory (`agents/*/`) follows the same structure:
- `README.md` - Agent role and contract reference
- Implementation files should maintain contract compliance

### Working with Contracts

When modifying or implementing an agent:
1. Read the contract in `schemas/contracts/<agent>_contract.md`
2. Review `schemas/contracts/COMMON_CONVENTIONS.md` for shared requirements
3. Check `schemas/examples/<agent>_input.example.json` for input format
4. Ensure all outputs include required fields (run_id, provenance, confidence, etc.)

### Adding New Agents

When adding a new agent:
1. Create contract in `schemas/contracts/<agent>_contract.md`
2. Create example input in `schemas/examples/<agent>_input.example.json`
3. Create agent directory in `agents/<agent>/`
4. Add README.md with role description and contract reference
5. Ensure compliance with `COMMON_CONVENTIONS.md`

## Implementation Notes

This repository currently contains design documentation and contracts but no implementation code. When implementing:
- Preserve data lineage in all transformations
- Return confidence scores for ambiguous mappings
- Create exception queues (like `exceptions_queue` in Classification Agent) for human review
- Log all warnings and errors with machine-readable structure
- Maintain schema versioning for contract evolution
