"""Configuration loading utilities."""

import yaml
import json
from pathlib import Path
from typing import Dict, List, Any


def load_config(config_path: str = None) -> Dict[str, Any]:
    """Load configuration from YAML file."""
    if config_path is None:
        # Default to config/config.yaml relative to this file
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    return config


def get_known_partners(master_data_path: str = None) -> List[Dict[str, str]]:
    """
    Load known partners from master_data.json.

    Returns:
        List of partner dicts with partner_id, partner_name, partner_code
    """
    if master_data_path is None:
        config = load_config()
        master_data_path = Path(__file__).parent.parent.parent.parent.parent / "schemas" / "master_data.json"

    try:
        with open(master_data_path, 'r') as f:
            master_data = json.load(f)

        partners = []
        if 'partners' in master_data:
            for partner in master_data['partners']:
                partners.append({
                    'partner_id': partner.get('partner_id'),
                    'partner_name': partner.get('partner_name'),
                    'partner_code': partner.get('partner_code'),
                    'status': partner.get('status', 'active')
                })

        # Filter to active partners only
        partners = [p for p in partners if p['status'] == 'active']

        return partners

    except FileNotFoundError:
        print(f"Warning: Master data file not found at {master_data_path}")
        return []
    except json.JSONDecodeError:
        print(f"Warning: Could not parse master data JSON at {master_data_path}")
        return []


def get_known_metrics(config_path: str = None) -> List[str]:
    """
    Get known metric names from config.

    Returns:
        List of known metric names
    """
    config = load_config(config_path)
    return config.get('known_metrics', [])


def get_canonical_schema(config_path: str = None) -> Dict[str, Any]:
    """Get canonical schema definition from config."""
    config = load_config(config_path)
    return config.get('canonical_schema', {})


def get_quality_rules(config_path: str = None) -> List[Dict[str, Any]]:
    """Get quality validation rules from config."""
    config = load_config(config_path)
    rules = config.get('quality_rules', [])
    # Filter to enabled rules only
    return [r for r in rules if r.get('enabled', True)]
