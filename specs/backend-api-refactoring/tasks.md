---
description: "Task list for Backend API Refactoring to align with Constitution v4.0.0"
---

# Tasks: Backend API Refactoring

**Input**: Constitution v4.0.0 - Backend API Development Standards  
**Prerequisites**: Existing backend codebase, Cloud SQL connection working  
**Goal**: Refactor existing backend structure to align with constitution principles

**Tests**: Tests are OPTIONAL - focus on ensuring existing functionality continues to work

**Organization**: Tasks are organized by foundational work, then API structure improvements.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- Include exact file paths in descriptions

## Path Conventions

- Backend: `meridian-backend/`
- Database: `meridian-backend/database/`
- API: `meridian-backend/api/`
- Services: `meridian-backend/services/`
- Models: `meridian-backend/models/` (Pydantic models)

---

## Phase 1: Cloud SQL Client Refactoring (Foundational)

**Purpose**: Convert existing `connect_with_connector` function to CloudSQLClient class without changing core logic

**⚠️ CRITICAL**: This phase must be complete before other refactoring can proceed

- [X] T001 Create CloudSQLClient class in meridian-backend/database/cloud_sql_client.py wrapping connect_with_connector function
- [X] T002 Convert connect_with_connector function to method in CloudSQLClient class preserving EXACT same logic
- [X] T003 Add __init__ method to CloudSQLClient class to initialize instance variables (pool, connector, env vars)
- [X] T004 Add get_connection method to CloudSQLClient class for getting connections from pool
- [X] T005 Add execute_query method to CloudSQLClient class using text() wrapper for SQLAlchemy 2.0+
- [X] T006 Add close method to CloudSQLClient class for cleanup and resource disposal
- [X] T007 Create get_db_client function in meridian-backend/database/cloud_sql_client.py that returns CloudSQLClient instance
- [X] T008 Update if __name__ == "__main__" block in meridian-backend/database/cloud_sql_client.py to use CloudSQLClient class
- [ ] T009 Test that connect_with_connector method works identically to original function

**Checkpoint**: CloudSQLClient class must work exactly like original function, all existing tests should pass

---

## Phase 2: Service Layer Updates

**Purpose**: Update services to properly use CloudSQLClient class

- [X] T010 Update ThreadService.__init__ in meridian-backend/services/thread_service.py to use CloudSQLClient instance
- [X] T011 Update ThreadService methods in meridian-backend/services/thread_service.py to use CloudSQLClient.get_connection() instead of async context manager
- [X] T012 Update MessageService.__init__ in meridian-backend/services/message_service.py to use CloudSQLClient instance
- [X] T013 Update MessageService methods in meridian-backend/services/message_service.py to use CloudSQLClient.get_connection()
- [X] T014 Update ChatService in meridian-backend/services/chat_service.py to use CloudSQLClient instance
- [X] T015 Update OpenAI service if it uses database in meridian-backend/services/openai_service.py
- [X] T016 Verify all services use parameterized queries through CloudSQLClient
- [X] T017 Update test files in meridian-backend/database/ to use CloudSQLClient class

**Checkpoint**: All services should use CloudSQLClient, no direct database connections

---

## Phase 3: API Structure Refactoring

**Purpose**: Create proper api/ directory structure and move endpoints from server.py

- [X] T018 Create meridian-backend/api/ directory with __init__.py
- [X] T019 Create meridian-backend/api/health.py with health check endpoints
- [X] T020 Move health check endpoints from meridian-backend/server.py to meridian-backend/api/health.py
- [X] T021 Create meridian-backend/api/threads.py with thread management endpoints
- [X] T022 Move thread endpoints (POST /api/threads, GET /api/threads, GET /api/threads/{id}, DELETE /api/threads/{id}) from meridian-backend/server.py to meridian-backend/api/threads.py
- [X] T023 Create meridian-backend/api/messages.py with message endpoints
- [X] T024 Move message endpoints (GET /api/threads/{id}/messages) from meridian-backend/server.py to meridian-backend/api/messages.py
- [X] T025 Create meridian-backend/api/chat.py with chat endpoint
- [X] T026 Move chat endpoint (POST /api/chat) from meridian-backend/server.py to meridian-backend/api/chat.py
- [X] T027 Create meridian-backend/api/auth.py with authentication endpoints
- [X] T028 Move auth endpoints (POST /api/auth/login, POST /api/auth/register, POST /api/auth/logout, POST /api/auth/google) from meridian-backend/server.py to meridian-backend/api/auth.py
- [X] T029 Create meridian-backend/api/agents.py with agents endpoints
- [X] T030 Move agents endpoints (POST /api/agents/analyze, GET /api/agents/health) from meridian-backend/server.py to meridian-backend/api/agents.py
- [X] T031 Update meridian-backend/server.py to import and include routers from api/ modules
- [X] T032 Ensure all API modules use APIRouter with proper prefix and tags
- [ ] T033 Verify all endpoints maintain same functionality after refactoring

**Checkpoint**: All endpoints moved to api/ directory, server.py only contains app setup and router includes

---

## Phase 4: Error Handling and Validation Improvements

**Purpose**: Ensure consistent error handling and validation across all APIs

- [X] T034 Review all API endpoints in meridian-backend/api/ for consistent error response format
- [X] T035 Update error responses to follow constitution format: { "error": "...", "detail": "...", "code": "..." }
- [X] T036 Ensure all endpoints use proper HTTP status codes (200, 201, 400, 404, 500, 502, 503)
- [X] T037 Add try-except blocks to all endpoints in meridian-backend/api/ with proper error handling
- [X] T038 Ensure database errors return 503 status code
- [X] T039 Ensure external service errors (OpenAI, Agents) return 502 status code
- [X] T040 Ensure validation errors return 400 with field-level details
- [ ] T041 Ensure all Pydantic models in meridian-backend/models/ have proper validation
- [X] T042 Add logging for all errors with full context (request_id, stack trace, user context)
- [ ] T043 Verify error responses don't expose sensitive information in production

**Checkpoint**: All endpoints have consistent error handling, proper status codes, and secure error messages

---

## Phase 5: Code Quality Improvements

**Purpose**: Ensure code follows constitution quality standards

- [X] T044 Add type hints to all CloudSQLClient methods in meridian-backend/database/cloud_sql_client.py
- [X] T045 Add docstrings to all CloudSQLClient methods following Google/NumPy style
- [ ] T046 Review all service methods in meridian-backend/services/ for type hints and docstrings
- [ ] T047 Review all API endpoint functions in meridian-backend/api/ for type hints and docstrings
- [ ] T048 Ensure all functions follow PEP 8 style guidelines
- [ ] T049 Remove any code duplication across services
- [ ] T050 Ensure all magic numbers and strings are constants
- [ ] T051 Verify consistent naming conventions (snake_case for functions, PascalCase for classes)
- [ ] T052 Add inline comments for complex logic explaining "why" not "what"

**Checkpoint**: All code has type hints, docstrings, and follows PEP 8

---

## Phase 6: Testing and Validation

**Purpose**: Ensure all functionality works after refactoring

- [ ] T053 Test CloudSQLClient.connect_with_connector() method works identically to original function
- [ ] T054 Test all thread CRUD operations through updated ThreadService
- [ ] T055 Test all message operations through updated MessageService
- [ ] T056 Test chat endpoint with updated ChatService
- [ ] T057 Test all API endpoints return correct responses
- [ ] T058 Test error handling for invalid inputs (400 errors)
- [ ] T059 Test error handling for not found resources (404 errors)
- [ ] T060 Test error handling for database errors (503 errors)
- [ ] T061 Test error handling for external service errors (502 errors)
- [ ] T062 Verify all existing tests in meridian-backend/database/ still pass
- [ ] T063 Run integration tests to verify end-to-end flows work

**Checkpoint**: All tests pass, existing functionality verified

---

## Phase 7: Documentation and Cleanup

**Purpose**: Update documentation and clean up unused code

- [ ] T064 Update meridian-backend/database/cloud_sql_client.py docstring to document CloudSQLClient class
- [ ] T065 Update README or documentation to reflect new API structure
- [ ] T066 Remove any unused imports from refactored files
- [ ] T067 Remove any commented-out code
- [ ] T068 Verify all imports are correct after file moves
- [ ] T069 Update any configuration files that reference old file paths
- [ ] T070 Create or update API documentation (OpenAPI/Swagger should auto-generate from FastAPI)

**Checkpoint**: Documentation updated, codebase clean

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Cloud SQL Client)**: No dependencies - can start immediately
- **Phase 2 (Service Layer)**: Depends on Phase 1 completion - services need CloudSQLClient
- **Phase 3 (API Structure)**: Depends on Phase 2 completion - APIs use services
- **Phase 4 (Error Handling)**: Can run in parallel with Phase 3 (different concerns)
- **Phase 5 (Code Quality)**: Can run in parallel with Phase 4 (different concerns)
- **Phase 6 (Testing)**: Depends on Phases 1-5 completion - tests all changes
- **Phase 7 (Documentation)**: Depends on Phase 6 completion - documents final state

### Parallel Opportunities

- **Within Phase 1**: T002-T006 can be done in parallel (different methods)
- **Within Phase 2**: T010-T015 can be done in parallel (different services)
- **Within Phase 3**: T019-T030 can be done in parallel (different API modules)
- **Within Phase 4**: T034-T042 can be done in parallel (different endpoints)
- **Within Phase 5**: T044-T052 can be done in parallel (different files)
- **Within Phase 6**: T053-T061 can be done in parallel (different test scenarios)

---

## Implementation Strategy

### Incremental Refactoring

1. **Phase 1 First**: Get CloudSQLClient working - this is the foundation
2. **Phase 2 Next**: Update services to use new client - enables API work
3. **Phase 3 Then**: Move APIs to proper structure - improves organization
4. **Phases 4-5**: Improve error handling and code quality - can be done incrementally
5. **Phase 6**: Comprehensive testing - validates all changes
6. **Phase 7**: Final polish - documentation and cleanup

### Risk Mitigation

- Test after each phase to ensure nothing breaks
- Keep original function logic intact (Phase 1)
- Move endpoints incrementally (Phase 3)
- Maintain backward compatibility during transition
- Use feature flags if needed for gradual rollout

### Validation Points

- After Phase 1: Original function behavior preserved
- After Phase 2: All services work with new client
- After Phase 3: All endpoints accessible and functional
- After Phase 4: Error handling consistent and secure
- After Phase 5: Code quality standards met
- After Phase 6: All tests pass, functionality verified
- After Phase 7: Documentation complete, codebase clean

---

## Notes

- **Critical**: Do NOT change the core logic of `connect_with_connector` when converting to method
- All file paths are relative to project root
- Use dependency injection pattern for CloudSQLClient in services
- Maintain existing functionality throughout refactoring
- Test incrementally to catch issues early
- Follow constitution principles strictly
- Keep commits atomic (one logical change per commit)

---

**End of Tasks**

