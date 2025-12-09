# Tasks: Agent Server Enhancement

**Input**: Constitution (`.specify/memory/constitution.md`), Current Implementation (`meridian-agents/server.py`)  
**Prerequisites**: Constitution v2.0.0, Chat Session Management Guidelines

**Tests**: Tests are included to ensure constitution compliance and service reliability.

**Organization**: Tasks are organized by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Agent Service**: `meridian-agents/` at repository root
- **Server**: `meridian-agents/server.py`
- **Models**: `meridian-agents/models/` (to be created)
- **Utils**: `meridian-agents/utils/` (to be created)
- **Tests**: `meridian-agents/tests/` (to be created)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create models directory structure in meridian-agents/models/
- [X] T002 Create utils directory structure in meridian-agents/utils/
- [X] T003 Create tests directory structure in meridian-agents/tests/
- [X] T004 [P] Configure logging infrastructure in meridian-agents/utils/logging.py
- [X] T005 [P] Create environment configuration module in meridian-agents/utils/config.py
- [X] T006 [P] Setup pytest configuration in meridian-agents/pytest.ini
- [X] T007 [P] Create test utilities in meridian-agents/tests/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T008 Implement thread-safe graph initialization in meridian-agents/server.py
- [X] T009 [P] Create Pydantic response models in meridian-agents/models/responses.py
- [X] T010 [P] Create Pydantic request models in meridian-agents/models/requests.py
- [X] T011 Setup structured logging with JSON format in meridian-agents/utils/logging.py
- [X] T012 Configure environment variable validation in meridian-agents/utils/config.py
- [X] T013 Create error handling utilities in meridian-agents/utils/errors.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Enhanced Health Check Endpoint (Priority: P1) 🎯 MVP

**Goal**: Implement constitution-compliant health check endpoint with proper error handling and graph initialization verification

**Independent Test**: `curl http://localhost:8001/health` returns HTTP 200 with `status`, `service`, and `graph_initialized` fields. Graph initialization errors are caught and returned in response body without crashing service.

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T014 [P] [US1] Unit test for health endpoint success case in meridian-agents/tests/test_health.py
- [X] T015 [P] [US1] Unit test for health endpoint with graph initialization error in meridian-agents/tests/test_health.py
- [X] T016 [P] [US1] Integration test for health endpoint in meridian-agents/tests/integration/test_health_integration.py

### Implementation for User Story 1

- [X] T017 [US1] Update health endpoint to use response model in meridian-agents/server.py
- [X] T018 [US1] Add error handling with detailed logging in meridian-agents/server.py
- [X] T019 [US1] Ensure health endpoint returns HTTP 200 even on graph initialization failure in meridian-agents/server.py
- [X] T020 [US1] Add response time validation (< 5 seconds) in meridian-agents/server.py
- [X] T021 [US1] Add structured logging for health check requests in meridian-agents/server.py

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Enhanced Analysis Endpoint with Context Support (Priority: P2)

**Goal**: Enhance analyze endpoint to accept conversation context and return structured responses with proper error handling

**Independent Test**: `POST /analyze` with `company_name`, `trade_date`, and optional `conversation_context` returns structured response with `company`, `date`, `decision`, and `state`. Errors return HTTP 500 with detailed traceback.

### Tests for User Story 2

- [X] T022 [P] [US2] Unit test for analyze endpoint with valid request in meridian-agents/tests/test_analyze.py
- [X] T023 [P] [US2] Unit test for analyze endpoint with conversation context in meridian-agents/tests/test_analyze.py
- [X] T024 [P] [US2] Unit test for analyze endpoint error handling in meridian-agents/tests/test_analyze.py
- [X] T025 [P] [US2] Integration test for full analysis workflow in meridian-agents/tests/integration/test_analyze_integration.py

### Implementation for User Story 2

- [X] T026 [US2] Update AnalyzeRequest model to include optional conversation_context in meridian-agents/models/requests.py
- [X] T027 [US2] Create AnalyzeResponse model in meridian-agents/models/responses.py
- [X] T028 [US2] Update analyze endpoint to use response model in meridian-agents/server.py
- [X] T029 [US2] Add conversation context processing logic in meridian-agents/server.py
- [X] T030 [US2] Enhance error handling with structured logging in meridian-agents/server.py
- [X] T031 [US2] Add request timeout handling (300 seconds) in meridian-agents/server.py
- [X] T032 [US2] Add input validation for company_name and trade_date in meridian-agents/server.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently

---

## Phase 5: User Story 3 - Thread-Safe Graph Initialization (Priority: P3)

**Goal**: Implement thread-safe graph initialization to prevent race conditions in concurrent request handling

**Independent Test**: Multiple concurrent requests to `/analyze` endpoint do not cause race conditions or duplicate graph initialization. Graph is initialized exactly once.

### Tests for User Story 3

- [X] T033 [P] [US3] Unit test for thread-safe graph initialization in meridian-agents/tests/test_graph_init.py
- [X] T034 [P] [US3] Concurrency test for multiple simultaneous requests in meridian-agents/tests/test_graph_init.py
- [X] T035 [P] [US3] Integration test for concurrent analyze requests in meridian-agents/tests/integration/test_concurrent_requests.py

### Implementation for User Story 3

- [X] T036 [US3] Add threading lock for graph initialization in meridian-agents/server.py
- [X] T037 [US3] Implement double-check locking pattern in get_graph() function in meridian-agents/server.py
- [X] T038 [US3] Add graph initialization state tracking in meridian-agents/server.py
- [X] T039 [US3] Handle graph initialization errors gracefully without blocking service in meridian-agents/server.py
- [X] T040 [US3] Add logging for graph initialization events in meridian-agents/server.py

**Checkpoint**: All user stories should now be independently functional with thread-safe operations

---

## Phase 6: User Story 4 - Comprehensive Logging and Monitoring (Priority: P4)

**Goal**: Implement structured logging with proper log levels, request tracking, and error context

**Independent Test**: All requests generate structured logs with request ID, endpoint, timestamp, and error context. Logs are in JSON format for easy parsing.

### Tests for User Story 4

- [X] T041 [P] [US4] Unit test for structured logging format in meridian-agents/tests/test_logging.py
- [X] T042 [P] [US4] Unit test for request ID generation and tracking in meridian-agents/tests/test_logging.py
- [X] T043 [P] [US4] Integration test for log output format in meridian-agents/tests/integration/test_logging_integration.py

### Implementation for User Story 4

- [X] T044 [US4] Implement structured JSON logging in meridian-agents/utils/logging.py
- [X] T045 [US4] Add request ID middleware for request tracking in meridian-agents/server.py
- [X] T046 [US4] Add logging decorator for endpoint requests in meridian-agents/utils/logging.py (implemented via middleware)
- [X] T047 [US4] Implement error context capture in meridian-agents/utils/errors.py
- [X] T048 [US4] Add log level configuration via environment variable in meridian-agents/utils/config.py
- [X] T049 [US4] Add performance logging for slow requests in meridian-agents/server.py
- [X] T050 [US4] Ensure sensitive data (API keys) is not logged in meridian-agents/utils/logging.py

**Checkpoint**: All endpoints now have comprehensive logging and monitoring

---

## Phase 7: User Story 5 - Enhanced Error Handling (Priority: P5)

**Goal**: Implement comprehensive error handling with proper HTTP status codes, detailed error messages, and sanitized production error responses

**Independent Test**: All errors return appropriate HTTP status codes (400 for validation, 500 for server errors). Error responses include detailed messages in development and sanitized messages in production.

### Tests for User Story 5

- [X] T051 [P] [US5] Unit test for validation error handling in meridian-agents/tests/test_errors.py
- [X] T052 [P] [US5] Unit test for server error handling in meridian-agents/tests/test_errors.py
- [X] T053 [P] [US5] Unit test for error sanitization in production mode in meridian-agents/tests/test_errors.py
- [X] T054 [P] [US5] Integration test for error response format in meridian-agents/tests/integration/test_error_handling.py

### Implementation for User Story 5

- [X] T055 [US5] Create custom exception classes in meridian-agents/utils/errors.py
- [X] T056 [US5] Implement global exception handler in meridian-agents/server.py
- [X] T057 [US5] Add error response models in meridian-agents/models/responses.py
- [X] T058 [US5] Implement error sanitization for production in meridian-agents/utils/errors.py
- [X] T059 [US5] Add validation error handling for Pydantic models in meridian-agents/server.py
- [X] T060 [US5] Add error logging with full context in meridian-agents/utils/errors.py
- [X] T061 [US5] Ensure stack traces only in development mode in meridian-agents/utils/errors.py

**Checkpoint**: All errors are handled consistently with proper status codes and logging

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T062 [P] Add OpenAPI documentation enhancements in meridian-agents/server.py
- [X] T063 [P] Add request/response examples to API documentation in meridian-agents/server.py
- [X] T064 [P] Create API usage documentation in docs/agents_api_reference.md
- [ ] T065 [P] Add performance benchmarks in meridian-agents/tests/benchmarks/ (optional - can be added later)
- [X] T066 Code cleanup and refactoring across all modules
- [X] T067 [P] Add integration tests for full workflow in meridian-agents/tests/integration/
- [X] T068 Security hardening (input validation, rate limiting considerations) - Input validation implemented
- [X] T069 [P] Add Docker health check validation in Dockerfile.agents
- [X] T070 Update README with service setup and testing instructions
- [ ] T071 Run full test suite and ensure > 70% coverage (52/53 tests passing, coverage can be verified)
- [X] T072 Validate all tasks against constitution compliance checklist

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3 → P4 → P5)
- **Polish (Final Phase)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Depends on US1 response models
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 4 (P4)**: Can start after Foundational (Phase 2) - Enhances all previous stories
- **User Story 5 (P5)**: Can start after Foundational (Phase 2) - Enhances all previous stories

### Within Each User Story

- Tests (if included) MUST be written and FAIL before implementation
- Models before services
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Foundational tasks marked [P] can run in parallel (within Phase 2)
- Once Foundational phase completes, user stories can start in parallel (if team capacity allows)
- All tests for a user story marked [P] can run in parallel
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# Launch all tests for User Story 1 together:
Task: "Unit test for health endpoint success case in meridian-agents/tests/test_health.py"
Task: "Unit test for health endpoint with graph initialization error in meridian-agents/tests/test_health.py"
Task: "Integration test for health endpoint in meridian-agents/tests/integration/test_health_integration.py"
```

---

## Parallel Example: User Story 2

```bash
# Launch all tests for User Story 2 together:
Task: "Unit test for analyze endpoint with valid request in meridian-agents/tests/test_analyze.py"
Task: "Unit test for analyze endpoint with conversation context in meridian-agents/tests/test_analyze.py"
Task: "Unit test for analyze endpoint error handling in meridian-agents/tests/test_analyze.py"
Task: "Integration test for full analysis workflow in meridian-agents/tests/integration/test_analyze_integration.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Enhanced Health Check)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Add User Story 4 → Test independently → Deploy/Demo
6. Add User Story 5 → Test independently → Deploy/Demo
7. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (Health Check)
   - Developer B: User Story 2 (Analysis Endpoint)
   - Developer C: User Story 3 (Thread Safety)
3. Then:
   - Developer A: User Story 4 (Logging)
   - Developer B: User Story 5 (Error Handling)
4. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence
- All tasks must comply with constitution principles
- Test coverage target: > 70% for production code

---

## Summary

**Total Tasks**: 72
- **Phase 1 (Setup)**: 7 tasks
- **Phase 2 (Foundational)**: 6 tasks
- **Phase 3 (US1 - Health Check)**: 8 tasks (3 tests + 5 implementation)
- **Phase 4 (US2 - Analysis Endpoint)**: 11 tasks (4 tests + 7 implementation)
- **Phase 5 (US3 - Thread Safety)**: 8 tasks (3 tests + 5 implementation)
- **Phase 6 (US4 - Logging)**: 10 tasks (3 tests + 7 implementation)
- **Phase 7 (US5 - Error Handling)**: 11 tasks (4 tests + 7 implementation)
- **Phase 8 (Polish)**: 11 tasks

**Parallel Opportunities**: 
- Setup phase: 4 parallel tasks
- Foundational phase: 3 parallel tasks
- Each user story: 3-4 parallel test tasks
- User stories 1-5 can be worked on in parallel after foundational phase

**Suggested MVP Scope**: Phases 1, 2, and 3 (User Story 1 - Enhanced Health Check)

**Independent Test Criteria**:
- **US1**: Health endpoint returns HTTP 200 with proper structure, handles errors gracefully
- **US2**: Analyze endpoint accepts context, returns structured response, handles errors
- **US3**: Graph initialization is thread-safe, no race conditions
- **US4**: All requests generate structured logs with proper context
- **US5**: All errors return appropriate status codes with proper error messages

