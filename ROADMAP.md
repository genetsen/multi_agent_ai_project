# Project Roadmap

## Phase 0 – Data Intake Automation
- [x] Design Email Scanner Agent
- [x] Define email classification patterns and scoring
- [x] Create contract and examples
- [ ] Implement email retrieval (Gmail API)
- [ ] Implement attachment/link extraction
- [ ] Build review queue interface
- [ ] Connect to Data Harmonization Agent

## Phase 1 – Foundations
- [x] Define canonical schemas
- [x] Design Data Harmonization Agent (full technical design)
- [x] Define schema mapping prompts and rules
- [ ] Implement Data Harmonization Agent
- [ ] Establish ingestion logging and traceability
- [ ] Build feedback loop for mapping corrections

## Phase 2 – Intelligence Layer
- [ ] Implement Classification Agent
- [ ] Add confidence scoring
- [ ] Introduce human review loop for taxonomy mapping

## Phase 3 – Trust & Validation
- [ ] Build Quality Assurance Agent
- [ ] Build Dashboard Validation Agent
- [ ] Create metric variance explanations

## Phase 4 – Operational Awareness
- [ ] Implement Project Tracker Agent
- [ ] Integrate email, Slack, meeting ingestion
- [ ] Auto-generate project narratives and status updates

---

## Implementation Priority

| Agent | Status | Next Steps |
|-------|--------|------------|
| Email Scanner | Design complete | Implement Gmail API integration |
| Data Harmonization | Design complete | Implement core transform engine |
| Classification | Contract defined | Await harmonization implementation |
| Quality Assurance | Contract defined | Await classification implementation |
| Dashboard Validation | Contract defined | Await QA implementation |
| Project Tracker | Contract defined | Can be implemented in parallel |

## Maintenance / Ops
- [ ] Refresh `schemas/master_data.json` (clients/campaigns/partners/packages/project types) from `gs://gs_data_model/prisma/prisma_master_filtered.csv` roughly monthly (scheduled job or CI).
