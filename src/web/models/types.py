# File: src/web/models/types.py

from typing import TypedDict, List, Literal, Optional

# Definisce il tipo di stato per le operazioni in background
class OperationStatus(TypedDict, total=False):
    status: Literal["running", "completed", "completed_with_errors", "error"]
    started_at: str
    completed_at: Optional[str]
    
    # Common fields
    total: int
    operation: Literal["start_group", "stop_group"]
    group_name: str
    containers: List[str] # Nomi dei container interessati
    errors: List[str]
    error: Optional[str]

    # Start specific fields
    started: Optional[int]
    already_running: Optional[int]
    
    # Stop specific fields
    stopped: Optional[int]
    not_running: Optional[int]
    
    # Failure field
    failed: Optional[int]