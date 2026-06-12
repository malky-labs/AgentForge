import pytest
import json
from app.services.workflow_runner import workflow_runner

def test_workflow_cycle_detection():
    # Simple self loop graph
    nodes = {
        "nodeA": {"id": "nodeA", "data": {}},
        "nodeB": {"id": "nodeB", "data": {}}
    }
    adj_list = {
        "nodeA": ["nodeB"],
        "nodeB": ["nodeA"]
    }
    in_degrees = {
        "nodeA": 1,
        "nodeB": 1
    }
    
    with pytest.raises(Exception) as exc_info:
        workflow_runner.check_for_cycles(nodes, adj_list, in_degrees)
    
    assert "Cycle detected" in str(exc_info.value)

def test_graph_parsing_and_connections():
    graph_json = {
        "nodes": [
            {"id": "node1", "type": "agentNode", "data": {"prompt": "task1"}},
            {"id": "node2", "type": "toolNode", "data": {"toolName": "python_sandbox"}}
        ],
        "edges": [
            {"source": "node1", "target": "node2"}
        ]
    }
    
    nodes, adj_list, in_degrees = workflow_runner._parse_graph(json.dumps(graph_json))
    
    assert len(nodes) == 2
    assert "node2" in adj_list["node1"]
    assert in_degrees["node2"] == 1
    assert in_degrees["node1"] == 0
