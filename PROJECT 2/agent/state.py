"""
LangGraph TypedDict AgentState definition.
"""

from typing import TypedDict, List, Dict, Any, Optional

class AgentState(TypedDict):
    question: str
    plan: List[str]
    sql_query: str
    sql_valid: bool
    sql_error: Optional[str]
    sql_records: List[Dict[str, Any]]
    sql_columns: List[str]
    calc_result: Dict[str, Any]
    verification: Dict[str, Any]
    chart_dict: Optional[Dict[str, Any]]
    chart_json: Optional[str]
    chart_type: Optional[str]
    insights: str
    retry_count: int
    messages: List[Dict[str, str]]
    metadata: Dict[str, Any]
