import json
import os
from typing import Dict

def validate_claim(claim: str) -> Dict:
    """Mock function to validate a claim against policy fixtures."""
    print(f"Policy MCP: Validating claim: {claim}")
    
    # Resolve path to fixtures relative to this file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fixtures_path = os.path.join(base_dir, 'demo_data', 'knowledge', 'approved_claims.json')
    
    try:
        with open(fixtures_path, 'r') as f:
            data = json.load(f)
            for item in data:
                if item['text'].lower() in claim.lower() or claim.lower() in item['text'].lower():
                    return {
                        "status": "success",
                        "claim": claim,
                        "is_valid": True,
                        "reason": f"Matches allowed claim: {item['text']}"
                    }
    except Exception as e:
        print(f"Error reading policy fixtures: {e}")
        
    return {
        "status": "success",
        "claim": claim,
        "is_valid": False,
        "reason": "Unsupported claim or policy violation"
    }

def check_compliance(text: str) -> Dict:
    """Mock function to check text for compliance."""
    print(f"Policy MCP: Checking compliance for text")
    return {
        "status": "success",
        "compliant": True,
        "findings": []
    }
