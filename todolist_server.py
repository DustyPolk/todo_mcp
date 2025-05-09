import asyncio
import json
import os
import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Any, Union
from fastmcp import FastMCP
import aiofiles
import shutil

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("TodoListServer")

# Get todo file path from environment variable or use default
TODO_FILE = os.environ.get("TODO_FILE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "todos.json"))
BACKUP_DIR = os.environ.get("TODO_BACKUP_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups"))

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

# Valid status values
VALID_STATUSES = ["pending", "in_progress", "done", "cancelled"]

# Valid priority values
VALID_PRIORITIES = ["low", "medium", "high", "critical"]

class TodoManager:
    """Manager class for todo operations"""
    
    def __init__(self, file_path: str, backup_dir: str):
        """Initialize the TodoManager with file path and backup directory"""
        self.file_path = file_path
        self.backup_dir = backup_dir
        self._todos_cache = None
        self._last_load_time = None
    
    async def _load_todos(self, force_reload: bool = False) -> List[dict]:
        """Load todos from file with caching"""
        current_time = datetime.now()
        
        # Use cache if available and not forced to reload
        if not force_reload and self._todos_cache is not None and self._last_load_time is not None:
            # Cache for 5 seconds
            if (current_time - self._last_load_time).total_seconds() < 5:
                return self._todos_cache.copy()
        
        try:
            if not os.path.exists(self.file_path):
                logger.info(f"Todo file not found at {self.file_path}. Creating new file.")
                self._todos_cache = []
                self._last_load_time = current_time
                return []
            
            async with aiofiles.open(self.file_path, mode="r") as f:
                content = await f.read()
                try:
                    todos = json.loads(content)
                    self._todos_cache = todos
                    self._last_load_time = current_time
                    return todos.copy()
                except json.JSONDecodeError as e:
                    logger.error(f"Error decoding JSON: {e}")
                    # If file exists but is corrupted, create backup
                    await self._create_backup(suffix="corrupted")
                    self._todos_cache = []
                    self._last_load_time = current_time
                    return []
        except Exception as e:
            logger.error(f"Error loading todos: {e}")
            self._todos_cache = []
            self._last_load_time = current_time
            return []
    
    async def _save_todos(self, todos: List[dict]) -> bool:
        """Save todos to file and update cache"""
        try:
            # Create backup before saving
            await self._create_backup()
            
            async with aiofiles.open(self.file_path, mode="w") as f:
                await f.write(json.dumps(todos, indent=2))
            
            # Update cache
            self._todos_cache = todos.copy()
            self._last_load_time = datetime.now()
            return True
        except Exception as e:
            logger.error(f"Error saving todos: {e}")
            return False
    
    async def _create_backup(self, suffix: str = None) -> str:
        """Create a backup of the todos file"""
        if not os.path.exists(self.file_path):
            return None
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix_str = f"_{suffix}" if suffix else ""
        backup_filename = f"todos_backup_{timestamp}{suffix_str}.json"
        backup_path = os.path.join(self.backup_dir, backup_filename)
        
        try:
            # Ensure backup directory exists
            os.makedirs(self.backup_dir, exist_ok=True)
            
            # Copy the file
            shutil.copy2(self.file_path, backup_path)
            logger.info(f"Created backup at {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Error creating backup: {e}")
            return None
    
    def _validate_date(self, date_str: str) -> bool:
        """Validate date string format (YYYY-MM-DD)"""
        if not date_str:
            return True
            
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return True
        except ValueError:
            return False
    
    def _validate_todo(self, todo: dict) -> List[str]:
        """Validate todo data and return list of errors"""
        errors = []
        
        # Validate title
        if not todo.get("title"):
            errors.append("Title is required")
        elif len(todo.get("title", "")) > 100:
            errors.append("Title must be less than 100 characters")
        
        # Validate description
        if len(todo.get("description", "")) > 1000:
            errors.append("Description must be less than 1000 characters")
        
        # Validate due date
        if todo.get("due_date") and not self._validate_date(todo.get("due_date")):
            errors.append("Due date must be in YYYY-MM-DD format")
        
        # Validate status
        if todo.get("status") and todo.get("status") not in VALID_STATUSES:
            errors.append(f"Status must be one of: {', '.join(VALID_STATUSES)}")
        
        # Validate priority
        if todo.get("priority") and todo.get("priority") not in VALID_PRIORITIES:
            errors.append(f"Priority must be one of: {', '.join(VALID_PRIORITIES)}")
        
        # Validate tags
        if todo.get("tags") and not isinstance(todo.get("tags"), list):
            errors.append("Tags must be a list")
        
        return errors
    
    def _serialize_todo(self, todo: dict) -> dict:
        """Serialize todo object for output"""
        return {
            "id": todo["id"],
            "title": todo["title"],
            "description": todo.get("description", ""),
            "due_date": todo.get("due_date"),
            "status": todo.get("status", "pending"),
            "priority": todo.get("priority", "medium"),
            "tags": todo.get("tags", []),
            "created_at": todo.get("created_at"),
            "updated_at": todo.get("updated_at")
        }
    
    async def add_todo(self, title: str, description: str = "", due_date: Optional[str] = None,
                      status: str = "pending", priority: str = "medium", tags: List[str] = None) -> Dict[str, Any]:
        """Add a new todo item"""
        # Validate inputs
        todo = {
            "title": title,
            "description": description,
            "due_date": due_date,
            "status": status,
            "priority": priority,
            "tags": tags or [],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        validation_errors = self._validate_todo(todo)
        if validation_errors:
            return {"success": False, "errors": validation_errors}
        
        # Load existing todos
        todos = await self._load_todos(force_reload=True)
        
        # Generate new ID
        todo_id = max([t["id"] for t in todos], default=0) + 1
        todo["id"] = todo_id
        
        # Add new todo
        todos.append(todo)
        
        # Save todos
        if await self._save_todos(todos):
            return {"success": True, "todo": self._serialize_todo(todo)}
        else:
            return {"success": False, "errors": ["Failed to save todo"]}
    
    async def list_todos(self, status: Optional[str] = None, priority: Optional[str] = None,
                        search: Optional[str] = None, tag: Optional[str] = None,
                        due_date_filter: Optional[str] = None, sort_by: str = "id",
                        sort_order: str = "asc", limit: int = 100, offset: int = 0) -> Dict[str, Any]:
        """List todos with filtering, sorting and pagination"""
        todos = await self._load_todos()
        filtered_todos = todos.copy()
        
        # Apply filters
        if status:
            if status not in VALID_STATUSES:
                return {"success": False, "errors": [f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"]}
            filtered_todos = [t for t in filtered_todos if t.get("status") == status]
        
        if priority:
            if priority not in VALID_PRIORITIES:
                return {"success": False, "errors": [f"Invalid priority. Must be one of: {', '.join(VALID_PRIORITIES)}"]}
            filtered_todos = [t for t in filtered_todos if t.get("priority") == priority]
        
        if search:
            search_lower = search.lower()
            filtered_todos = [t for t in filtered_todos if 
                             search_lower in t.get("title", "").lower() or 
                             search_lower in t.get("description", "").lower()]
        
        if tag:
            filtered_todos = [t for t in filtered_todos if tag in t.get("tags", [])]
        
        if due_date_filter:
            today = date.today().isoformat()
            
            if due_date_filter == "overdue":
                filtered_todos = [t for t in filtered_todos if t.get("due_date") and t.get("due_date") < today]
            elif due_date_filter == "today":
                filtered_todos = [t for t in filtered_todos if t.get("due_date") == today]
            elif due_date_filter == "upcoming":
                filtered_todos = [t for t in filtered_todos if t.get("due_date") and t.get("due_date") > today]
            elif due_date_filter == "no_date":
                filtered_todos = [t for t in filtered_todos if not t.get("due_date")]
            else:
                return {"success": False, "errors": ["Invalid due_date_filter. Must be one of: overdue, today, upcoming, no_date"]}
        
        # Apply sorting
        valid_sort_fields = ["id", "title", "due_date", "status", "priority", "created_at", "updated_at"]
        if sort_by not in valid_sort_fields:
            return {"success": False, "errors": [f"Invalid sort_by. Must be one of: {', '.join(valid_sort_fields)}"]}
        
        reverse = sort_order.lower() == "desc"
        filtered_todos.sort(key=lambda x: x.get(sort_by, ""), reverse=reverse)
        
        # Apply pagination
        total_count = len(filtered_todos)
        paginated_todos = filtered_todos[offset:offset + limit]
        
        # Serialize todos
        serialized_todos = [self._serialize_todo(t) for t in paginated_todos]
        
        return {
            "success": True,
            "todos": serialized_todos,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }
    
    async def get_todo(self, todo_id: int) -> Dict[str, Any]:
        """Get a todo by id"""
        todos = await self._load_todos()
        
        for todo in todos:
            if todo["id"] == todo_id:
                return {"success": True, "todo": self._serialize_todo(todo)}
        
        return {"success": False, "errors": [f"Todo {todo_id} not found"]}
    
    async def update_todo(self, todo_id: int, title: Optional[str] = None, 
                         description: Optional[str] = None, due_date: Optional[str] = None,
                         status: Optional[str] = None, priority: Optional[str] = None,
                         tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Update a todo by id"""
        todos = await self._load_todos(force_reload=True)
        
        # Find todo by id
        todo_index = None
        for i, todo in enumerate(todos):
            if todo["id"] == todo_id:
                todo_index = i
                break
        
        if todo_index is None:
            return {"success": False, "errors": [f"Todo {todo_id} not found"]}
        
        # Create updated todo
        updated_todo = todos[todo_index].copy()
        
        # Update fields if provided
        if title is not None:
            updated_todo["title"] = title
        if description is not None:
            updated_todo["description"] = description
        if due_date is not None:
            updated_todo["due_date"] = due_date
        if status is not None:
            updated_todo["status"] = status
        if priority is not None:
            updated_todo["priority"] = priority
        if tags is not None:
            updated_todo["tags"] = tags
        
        # Update timestamp
        updated_todo["updated_at"] = datetime.now().isoformat()
        
        # Validate updated todo
        validation_errors = self._validate_todo(updated_todo)
        if validation_errors:
            return {"success": False, "errors": validation_errors}
        
        # Update todo in list
        todos[todo_index] = updated_todo
        
        # Save todos
        if await self._save_todos(todos):
            return {"success": True, "todo": self._serialize_todo(updated_todo)}
        else:
            return {"success": False, "errors": ["Failed to save todo"]}
    
    async def complete_todo(self, todo_id: int) -> Dict[str, Any]:
        """Mark a todo as complete by id"""
        return await self.update_todo(todo_id, status="done")
    
    async def delete_todo(self, todo_id: int) -> Dict[str, Any]:
        """Delete a todo by id"""
        todos = await self._load_todos(force_reload=True)
        
        # Find todo by id
        original_length = len(todos)
        new_todos = [t for t in todos if t["id"] != todo_id]
        
        if len(new_todos) == original_length:
            return {"success": False, "errors": [f"Todo {todo_id} not found"]}
        
        # Save todos
        if await self._save_todos(new_todos):
            return {"success": True, "message": f"Todo {todo_id} deleted"}
        else:
            return {"success": False, "errors": ["Failed to save todos"]}
    
    async def batch_delete_todos(self, todo_ids: List[int]) -> Dict[str, Any]:
        """Delete multiple todos by ids"""
        todos = await self._load_todos(force_reload=True)
        
        # Find todos by ids
        original_length = len(todos)
        new_todos = [t for t in todos if t["id"] not in todo_ids]
        
        deleted_count = original_length - len(new_todos)
        if deleted_count == 0:
            return {"success": False, "errors": ["No matching todos found"]}
        
        # Save todos
        if await self._save_todos(new_todos):
            return {"success": True, "message": f"{deleted_count} todos deleted"}
        else:
            return {"success": False, "errors": ["Failed to save todos"]}
    
    async def create_backup(self) -> Dict[str, Any]:
        """Create a manual backup of the todos file"""
        backup_path = await self._create_backup(suffix="manual")
        
        if backup_path:
            return {"success": True, "backup_path": backup_path}
        else:
            return {"success": False, "errors": ["Failed to create backup"]}
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about todos"""
        todos = await self._load_todos()
        
        # Count by status
        status_counts = {}
        for status in VALID_STATUSES:
            status_counts[status] = len([t for t in todos if t.get("status") == status])
        
        # Count by priority
        priority_counts = {}
        for priority in VALID_PRIORITIES:
            priority_counts[priority] = len([t for t in todos if t.get("priority") == priority])
        
        # Count by due date
        today = date.today().isoformat()
        overdue_count = len([t for t in todos if t.get("due_date") and t.get("due_date") < today])
        due_today_count = len([t for t in todos if t.get("due_date") == today])
        upcoming_count = len([t for t in todos if t.get("due_date") and t.get("due_date") > today])
        no_date_count = len([t for t in todos if not t.get("due_date")])
        
        # Get all tags
        all_tags = set()
        for todo in todos:
            all_tags.update(todo.get("tags", []))
        
        # Count by tag
        tag_counts = {}
        for tag in all_tags:
            tag_counts[tag] = len([t for t in todos if tag in t.get("tags", [])])
        
        return {
            "success": True,
            "total_count": len(todos),
            "status_counts": status_counts,
            "priority_counts": priority_counts,
            "due_date_counts": {
                "overdue": overdue_count,
                "today": due_today_count,
                "upcoming": upcoming_count,
                "no_date": no_date_count
            },
            "tag_counts": tag_counts
        }


# Initialize the MCP server
mcp = FastMCP(name="ToDoListServer")

# Initialize the TodoManager
todo_manager = TodoManager(TODO_FILE, BACKUP_DIR)

@mcp.tool()
async def add_todo(title: str, description: str = "", due_date: Optional[str] = None,
                  status: str = "pending", priority: str = "medium", tags: List[str] = None) -> Dict[str, Any]:
    """
    Add a new todo item.
    
    Args:
        title: The title of the todo (required, max 100 chars)
        description: A detailed description (optional, max 1000 chars)
        due_date: Due date in YYYY-MM-DD format (optional)
        status: Status of the todo (optional, one of: pending, in_progress, done, cancelled)
        priority: Priority level (optional, one of: low, medium, high, critical)
        tags: List of tags for categorization (optional)
    
    Returns:
        Dict containing success status and todo data or error messages
    """
    return await todo_manager.add_todo(title, description, due_date, status, priority, tags)

@mcp.tool()
async def list_todos(status: Optional[str] = None, priority: Optional[str] = None,
                    search: Optional[str] = None, tag: Optional[str] = None,
                    due_date_filter: Optional[str] = None, sort_by: str = "id",
                    sort_order: str = "asc", limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """
    List todos with filtering, sorting and pagination.
    
    Args:
        status: Filter by status (optional, one of: pending, in_progress, done, cancelled)
        priority: Filter by priority (optional, one of: low, medium, high, critical)
        search: Search in title and description (optional)
        tag: Filter by tag (optional)
        due_date_filter: Filter by due date (optional, one of: overdue, today, upcoming, no_date)
        sort_by: Field to sort by (optional, default: id)
        sort_order: Sort order (optional, one of: asc, desc, default: asc)
        limit: Maximum number of todos to return (optional, default: 100)
        offset: Number of todos to skip (optional, default: 0)
    
    Returns:
        Dict containing success status, todos list, and pagination info
    """
    return await todo_manager.list_todos(status, priority, search, tag, due_date_filter, sort_by, sort_order, limit, offset)

@mcp.tool()
async def get_todo(todo_id: int) -> Dict[str, Any]:
    """
    Get a todo by id.
    
    Args:
        todo_id: The ID of the todo to retrieve
    
    Returns:
        Dict containing success status and todo data or error message
    """
    return await todo_manager.get_todo(todo_id)

@mcp.tool()
async def update_todo(todo_id: int, title: Optional[str] = None, 
                     description: Optional[str] = None, due_date: Optional[str] = None,
                     status: Optional[str] = None, priority: Optional[str] = None,
                     tags: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Update a todo by id.
    
    Args:
        todo_id: The ID of the todo to update
        title: New title (optional)
        description: New description (optional)
        due_date: New due date in YYYY-MM-DD format (optional)
        status: New status (optional, one of: pending, in_progress, done, cancelled)
        priority: New priority (optional, one of: low, medium, high, critical)
        tags: New list of tags (optional)
    
    Returns:
        Dict containing success status and updated todo data or error messages
    """
    return await todo_manager.update_todo(todo_id, title, description, due_date, status, priority, tags)

@mcp.tool()
async def complete_todo(todo_id: int) -> Dict[str, Any]:
    """
    Mark a todo as complete by id.
    
    Args:
        todo_id: The ID of the todo to mark as complete
    
    Returns:
        Dict containing success status and updated todo data or error message
    """
    return await todo_manager.complete_todo(todo_id)

@mcp.tool()
async def delete_todo(todo_id: int) -> Dict[str, Any]:
    """
    Delete a todo by id.
    
    Args:
        todo_id: The ID of the todo to delete
    
    Returns:
        Dict containing success status and message or error
    """
    return await todo_manager.delete_todo(todo_id)

@mcp.tool()
async def batch_delete_todos(todo_ids: List[int]) -> Dict[str, Any]:
    """
    Delete multiple todos by ids.
    
    Args:
        todo_ids: List of todo IDs to delete
    
    Returns:
        Dict containing success status and message or error
    """
    return await todo_manager.batch_delete_todos(todo_ids)

@mcp.tool()
async def create_backup() -> Dict[str, Any]:
    """
    Create a manual backup of the todos file.
    
    Returns:
        Dict containing success status and backup path or error
    """
    return await todo_manager.create_backup()

@mcp.tool()
async def get_statistics() -> Dict[str, Any]:
    """
    Get statistics about todos.
    
    Returns:
        Dict containing counts by status, priority, due date, and tags
    """
    return await todo_manager.get_statistics()

if __name__ == "__main__":
    mcp.run()
