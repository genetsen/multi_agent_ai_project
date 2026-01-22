# Master Data (Cross-Agent): Clients, Campaigns, Partners, Packages, Project Types

This file defines **overarching master data** that can be referenced across all
agents and contracts.

The intent is to keep these concepts consistent across:
- ingestion + harmonization
- naming/taxonomy classification
- QA + validation
- project tracking and narrative

## Canonical entities

### Client
Represents the top-level business entity.

Required fields:
- `client_id` (string, stable internal id; e.g. `cli_apple`)
- `client_name` (string, display name)

Optional fields:
- `client_code` (string, short code used in file names, e.g. `APPLE`)
- `brand_family` (string)
- `regions[]` (strings)
- `status` (`active` | `inactive`)

### Campaign
Represents a marketing campaign for a client.

Required fields:
- `campaign_id` (string, stable internal id; e.g. `cam_apple_2026_q1_launch`)
- `client_id` (string)
- `campaign_name` (string)

Optional fields:
- `fiscal_year` (number)
- `quarter` (`Q1` | `Q2` | `Q3` | `Q4`)
- `start_date` (YYYY-MM-DD)
- `end_date` (YYYY-MM-DD)
- `objective` (string)
- `status` (`planned` | `live` | `paused` | `complete`)

### Partner
Represents a media partner / supplier / platform.

Required fields:
- `partner_id` (string, stable internal id; e.g. `par_miq`)
- `partner_name` (string)

Optional fields:
- `partner_code` (string)
- `external_keys` (object; e.g. `{ "prisma": "OX|GSP|7|MIQ" }`)
- `status` (`active` | `inactive`)

### Package
Represents the planning/execution package as defined in the Prisma export (identified by `PACKAGE_HEADER_PLACEMENT_ID`).

Required fields:
- `package_id` (string, stable internal id; often a platform key)
- `package_name` (string)

Optional fields:
- `client_id` (string)
- `campaign_id` (string)
- `partner_id` (string)
- `start_date` (YYYY-MM-DD)
- `end_date` (YYYY-MM-DD)
- `external_keys` (object)

### Project Type
Represents *what kind of work* is being performed (used for routing agents,
templates, validations, and expected outputs).

Required fields:
- `project_type_id` (string, stable id; e.g. `pt_media_reporting`)
- `project_type_name` (string)

Optional fields:
- `description` (string)
- `default_agents[]` (agent ids or folder names)
- `required_inputs[]` (strings)
- `expected_outputs[]` (strings)

## Shared identifiers

When applicable, any agent input/output payload should include one or more of:
- `client_id`
- `campaign_id`
- `partner_id`
- `package_id`
- `project_type_id`

If an identifier is unknown at runtime, agents should:
- preserve the raw values they observed (e.g. `client_name_raw`)
- emit a structured warning in `warnings[]`
- avoid guessing (prefer `null` + explanation)

## Suggested JSON format

This repository stores the data in `schemas/master_data.json`.

Top-level object:
- `schema_version`
- `clients[]`
- `campaigns[]`
- `partners[]`
- `packages[]`
- `project_types[]`

## Canonical source of truth

The canonical reference for master data is the filtered Prisma export:

- `gs://gs_data_model/prisma/prisma_master_filtered.csv`

This repository also stores a generated snapshot at:

- `schemas/master_data.json`

TODO: Add an automated job that refreshes `schemas/master_data.json` from the
canonical GCS source roughly once per month.
