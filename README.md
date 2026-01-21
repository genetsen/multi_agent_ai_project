# Multi-Agent AI System

This repository contains a modular, multi-agent system for harmonizing,
classifying, validating, and tracking media and analytics data.

Core docs:
- docs/project/project_plan.md
- ROADMAP.md
- schemas/contracts/ (agent handoff contracts)

Agents are designed to be composable: each agent consumes a well-defined input contract
and produces a well-defined output contract with confidence scores, provenance, and logs.
