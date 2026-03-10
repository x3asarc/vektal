"""Lightweight task tracking for agent visibility"""
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

TASK_FILE = Path(".tasks/active.json")

def create_task(subject: str, description: str, active_form: str) -> tuple[str, str]:
    """Create a task and return (task_id, user_message)"""
    TASK_FILE.parent.mkdir(exist_ok=True)

    tasks = {}
    if TASK_FILE.exists():
        tasks = json.loads(TASK_FILE.read_text())

    task_id = str(len(tasks) + 1)
    tasks[task_id] = {
        "subject": subject,
        "description": description,
        "activeForm": active_form,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    TASK_FILE.write_text(json.dumps(tasks, indent=2))
    message = f"📋 [Task {task_id}] {subject}"
    print(message)  # For logs
    return task_id, message

def update_task(task_id: str, status: str) -> str:
    """Update task status and return user message"""
    tasks = json.loads(TASK_FILE.read_text())
    tasks[task_id]["status"] = status
    tasks[task_id]["updated_at"] = datetime.now(timezone.utc).isoformat()
    TASK_FILE.write_text(json.dumps(tasks, indent=2))

    # Status emoji mapping
    emoji = {"pending": "⏸️", "in_progress": "🔄", "completed": "✅"}
    message = f"{emoji.get(status, '📌')} [Task {task_id}] {status.upper()}: {tasks[task_id]['subject']}"
    print(message)  # For logs
    return message

def list_tasks():
    """Show all tasks with status"""
    if not TASK_FILE.exists():
        print("No tasks yet")
        return

    tasks = json.loads(TASK_FILE.read_text())
    print("\n=== TASK LIST ===")
    for tid, task in tasks.items():
        status = task["status"]
        print(f"[{status}] {task['subject']}")
    print()
