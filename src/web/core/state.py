from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger("uvicorn")

# Global state for background operations
active_operations: Dict[str, dict] = {}


def create_operation(operation_id: str, operation_type: str, **kwargs) -> dict:
    """Create a new operation entry"""
    operation = {
        "operation_id": operation_id,
        "status": "running",
        "operation": operation_type,
        "started_at": datetime.now().isoformat(),
        "completed_at": None,
        "total": kwargs.get("total", 0),
        "errors": [],
        "scripts_running": [],  # Track script execution
        "scripts_completed": [],  # Track completed scripts
    }
    
    # Add type-specific fields
    if operation_type == "start_group":
        operation.update({
            "group_name": kwargs.get("group_name", ""),
            "containers": [],
            "started": 0,
            "already_running": 0,
            "failed": 0,
        })
    
    elif operation_type == "stop_group":
        operation.update({
            "group_name": kwargs.get("group_name", ""),
            "containers": [],
            "stopped": 0,
            "not_running": 0,
            "failed": 0,
        })
    
    elif operation_type == "start":
        operation.update({
            "container": kwargs.get("container", ""),
            "started": 0,
            "already_running": 0,
            "failed": 0,
        })

    elif operation_type == "stop":
        operation.update({
            "container": kwargs.get("container", ""),
            "stopped": 0,
            "not_running": 0,
            "failed": 0,
        })
    
    elif operation_type == "stop_all":
        operation.update({
            "stopped": 0,
            "containers": [],
        })
    
    elif operation_type == "restart_all":
        operation.update({
            "restarted": 0,
            "containers": [],
        })
    
    elif operation_type == "cleanup":
        operation.update({
            "removed": 0,
            "containers": [],
        })
    
    active_operations[operation_id] = operation
    logger.debug("Created operation %s: %s", operation_id, operation_type)
    
    return operation


def get_operation(operation_id: str) -> Dict[str, Any] | None:
    """Get operation by ID"""
    return active_operations.get(operation_id)


def update_operation(operation_id: str, **updates) -> bool:
    """Update operation fields"""
    if operation_id not in active_operations:
        logger.warning("Operation %s not found", operation_id)
        return False
    
    active_operations[operation_id].update(updates)
    return True


def add_script_tracking(operation_id: str, container: str, script_type: str) -> bool:
    """Track script execution start"""
    if operation_id not in active_operations:
        logger.warning("Operation %s not found when tracking script", operation_id)
        return False
    
    script_info = {
        "container": container,
        "type": script_type,
        "started_at": datetime.now().isoformat()
    }
    active_operations[operation_id]["scripts_running"].append(script_info)
    logger.debug("Added script tracking for %s: %s", container, script_type)
    return True


def complete_script_tracking(operation_id: str, container: str) -> bool:
    """Mark script execution as complete"""
    if operation_id not in active_operations:
        logger.warning("Operation %s not found when completing script", operation_id)
        return False
    
    running_scripts = active_operations[operation_id]["scripts_running"]
    completed_script = next((s for s in running_scripts if s["container"] == container), None)
    
    if completed_script:
        running_scripts.remove(completed_script)
        completed_script["completed_at"] = datetime.now().isoformat()
        active_operations[operation_id]["scripts_completed"].append(completed_script)
        logger.debug("Completed script tracking for %s", container)
        return True
    
    logger.warning("Script tracking not found for %s in operation %s", container, operation_id)
    return False


def complete_operation(operation_id: str, **final_updates) -> bool:
    """Mark operation as completed"""
    if operation_id not in active_operations:
        return False
    
    final_updates["status"] = "completed"
    final_updates["completed_at"] = datetime.now().isoformat()
    
    return update_operation(operation_id, **final_updates)


def fail_operation(operation_id: str, error: str, **extra_updates) -> bool:
    """Mark operation as failed"""
    if operation_id not in active_operations:
        return False
    
    updates = {
        "status": "error",
        "error": error,
        "completed_at": datetime.now().isoformat(),
    }
    updates.update(extra_updates)
    
    return update_operation(operation_id, **updates)


def cleanup_old_operations(max_age_seconds: int = 3600) -> int:
    """Remove completed operations older than max_age_seconds"""
    now = datetime.now()
    operations_to_remove = []
    
    for op_id, op_data in active_operations.items():
        if op_data.get("status") == "completed" and op_data.get("completed_at"):
            try:
                completed_at = datetime.fromisoformat(op_data["completed_at"])
                age = (now - completed_at).total_seconds()
                if age > max_age_seconds:
                    operations_to_remove.append(op_id)
            except ValueError:
                pass
    
    for op_id in operations_to_remove:
        del active_operations[op_id]
        logger.debug("Cleaned up old operation: %s", op_id)
    
    return len(operations_to_remove)