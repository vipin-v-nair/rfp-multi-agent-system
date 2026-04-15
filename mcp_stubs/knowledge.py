import json
import os
from typing import Dict, List

def get_evidence(query: str) -> Dict:
    """Mock function to retrieve evidence from fixtures."""
    print(f"Knowledge MCP: Retrieving evidence for query: {query}")
    
    # Resolve path to fixtures relative to this file
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fixtures_path = os.path.join(base_dir, 'demo_data', 'knowledge', 'approved_claims.json')
    
    try:
        with open(fixtures_path, 'r') as f:
            data = json.load(f)
            results = []
            for item in data:
                # Check if any word in query matches category or text
                if any(word in item['text'].lower() for word in query.lower().split() if len(word) > 3):
                    results.append(item['text'])
            if results:
                return {
                    "status": "success",
                    "query": query,
                    "evidence": results
                }
    except Exception as e:
        print(f"Error reading knowledge fixtures: {e}")
        
    return {
        "status": "success",
        "query": query,
        "evidence": ["No specific evidence found in corpus."]
    }

def get_approved_claims() -> List[str]:
    """Mock function to retrieve approved claims."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    fixtures_path = os.path.join(base_dir, 'demo_data', 'knowledge', 'approved_claims.json')
    try:
        with open(fixtures_path, 'r') as f:
            data = json.load(f)
            return [item['text'] for item in data]
    except Exception:
        return []
