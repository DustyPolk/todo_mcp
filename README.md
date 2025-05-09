# FastMCP Todo List Server

A powerful, feature-rich todo list server built with FastMCP that provides a comprehensive set of tools for managing todos. This server can be used with Claude Desktop to create, manage, and organize your tasks efficiently.

## Features

- **Rich Todo Management**: Create, read, update, and delete todos with extensive metadata
- **Advanced Filtering & Sorting**: Filter by status, priority, tags, due dates, and more
- **Search Capability**: Search todos by title and description
- **Automatic Backups**: Automatic backups before any data changes
- **Manual Backups**: Create manual backups on demand
- **Statistics**: Get detailed statistics about your todos
- **Data Validation**: Comprehensive validation for all inputs
- **Caching**: Efficient caching to reduce file I/O
- **Configurable**: Configurable file paths via environment variables

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/DustyPolk/todo_mcp.git
   cd todo_mcp
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv .venv
   # On Windows
   .venv\Scripts\activate
   # On macOS/Linux
   source .venv/bin/activate
   ```

3. Install the required packages:
   ```
   pip install fastmcp aiofiles
   ```

## Running the Server

Run the server with:

```
python todolist_server.py
```

The server will start and be available for Claude Desktop to connect to.

## Environment Variables

You can configure the server using the following environment variables:

- `TODO_FILE`: Path to the JSON file where todos are stored (default: `todos.json` in the same directory as the script)
- `TODO_BACKUP_DIR`: Path to the directory where backups are stored (default: `backups` in the same directory as the script)

## Available Tools

The server provides the following tools:

### `add_todo`

Add a new todo item.

**Parameters:**
- `title`: The title of the todo (required, max 100 chars)
- `description`: A detailed description (optional, max 1000 chars)
- `due_date`: Due date in YYYY-MM-DD format (optional)
- `status`: Status of the todo (optional, one of: pending, in_progress, done, cancelled)
- `priority`: Priority level (optional, one of: low, medium, high, critical)
- `tags`: List of tags for categorization (optional)

### `list_todos`

List todos with filtering, sorting and pagination.

**Parameters:**
- `status`: Filter by status (optional, one of: pending, in_progress, done, cancelled)
- `priority`: Filter by priority (optional, one of: low, medium, high, critical)
- `search`: Search in title and description (optional)
- `tag`: Filter by tag (optional)
- `due_date_filter`: Filter by due date (optional, one of: overdue, today, upcoming, no_date)
- `sort_by`: Field to sort by (optional, default: id)
- `sort_order`: Sort order (optional, one of: asc, desc, default: asc)
- `limit`: Maximum number of todos to return (optional, default: 100)
- `offset`: Number of todos to skip (optional, default: 0)

### `get_todo`

Get a todo by id.

**Parameters:**
- `todo_id`: The ID of the todo to retrieve

### `update_todo`

Update a todo by id.

**Parameters:**
- `todo_id`: The ID of the todo to update
- `title`: New title (optional)
- `description`: New description (optional)
- `due_date`: New due date in YYYY-MM-DD format (optional)
- `status`: New status (optional, one of: pending, in_progress, done, cancelled)
- `priority`: New priority (optional, one of: low, medium, high, critical)
- `tags`: New list of tags (optional)

### `complete_todo`

Mark a todo as complete by id.

**Parameters:**
- `todo_id`: The ID of the todo to mark as complete

### `delete_todo`

Delete a todo by id.

**Parameters:**
- `todo_id`: The ID of the todo to delete

### `batch_delete_todos`

Delete multiple todos by ids.

**Parameters:**
- `todo_ids`: List of todo IDs to delete

### `create_backup`

Create a manual backup of the todos file.

**Parameters:** None

### `get_statistics`

Get statistics about todos.

**Parameters:** None

## Data Structure

Todos are stored with the following structure:

```json
{
  "id": 1,
  "title": "Complete project report",
  "description": "Finish the quarterly project report",
  "due_date": "2025-05-20",
  "status": "pending",
  "priority": "high",
  "tags": ["work", "quarterly"],
  "created_at": "2025-05-09T12:00:00.000000",
  "updated_at": "2025-05-09T12:00:00.000000"
}
```

## License

MIT
