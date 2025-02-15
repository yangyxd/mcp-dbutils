# Changelog

All notable changes to this project will be documented in this file.

## [0.2.7] - 2025-02-15

### Added
- Added GitHub Actions workflow for automated testing
- Added PostgreSQL service in CI environment
- Added detailed test reporting with coverage in CI
- Added coverage badge to README using dynamic-badges-action

## [0.2.6] - 2025-02-12

### Added
- Added test coverage reporting with pytest-cov
- Added coverage configuration and HTML report generation
- Added test coverage tracking for all source code

## [0.2.5] - 2025-02-12

### Added
- Comprehensive automated tests for both PostgreSQL and SQLite handlers
- Integration tests for database operations
- Unit tests for configuration
- Test fixtures and Docker-based test environments

## [0.2.4] - 2025-02-09

### Changed
- Unified server configuration name to "dbutils"
- Improved documentation formatting and readability
- Added architecture diagrams
- Added contribution guidelines
- Enhanced installation instructions with environment variables
- Added acknowledgments section

## [0.2.3] - 2025-02-09

### Added
- Added comprehensive installation guides for uvx, pip, and Docker
- Added GitHub Actions workflow for automated PyPI releases
- Added both English and Chinese documentation
- Added project badges and repository information

### Changed
- Internationalized all code messages and docstrings
- Updated Python version requirement to 3.10+
- Improved documentation structure and examples
- Unified project naming to mcp-dbutils across all references

## [0.2.2] - 2025-02-09

### Added
- Added explicit database type declaration in configs
- Improved database type awareness in query results
- Standardized field naming across different database types

### Changed
- Unified response format for normal results and error messages
- Enhanced error reporting with database-specific details

## [0.2.1] - 2025-02-09

### Added
- SQLite database support with basic CRUD operations
- Password protection for SQLite databases
- Table schema inspection for SQLite
- URI connection string support for SQLite

### Fixed
- Automatic database type detection from config
- Connection handling improvements

## [0.2.0] - 2025-02-09

### Changed
- Renamed project from mcp-postgres to mcp-dbutils
- Restructured project for multi-database support
- Added base classes for database handling
- Improved configuration management
- Enhanced error handling and logging

## [0.1.1] - 2025-02-08

### Added
- Enhanced PostgreSQL error logging with error codes
- Improved error details with pgcode and pgerror
- Better error differentiation between PostgreSQL-specific and general errors

### Changed
- Maintained backwards compatibility while improving error flow

## [0.1.0] - 2025-02-08

### Added
- Initial PostgreSQL implementation
- YAML configuration for multiple databases
- Connection pool management
- Table structure querying
- Read-only SQL query execution
- Basic error handling and logging
