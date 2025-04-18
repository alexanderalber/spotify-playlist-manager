# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands
- Setup: `python -m venv venv && source venv/bin/activate && pip install -r requirements.txt`
- Run: `python app.py` (starts Flask app on port 8888)
- Initialize/update database: `python read_from_spotify.py`
- Create backup: `python backup.py`

## Code Style Guidelines
- Imports: standard lib → third-party → local imports
- Type hints: Use `typing` module for annotations (List, Dict, Optional, etc.)
- Naming: snake_case for functions/variables, PascalCase for classes, UPPER_SNAKE for constants
- SQL: Use parameterized queries, manage connections with context managers
- Error handling: Use @handle_errors decorator or try/except with specific exceptions
- Documentation: Include docstrings for functions/classes
- Functions: Follow single responsibility principle
- Database: Use the Database context manager for SQLite connections
- Flask: Protect routes with @require_auth and @handle_errors decorators