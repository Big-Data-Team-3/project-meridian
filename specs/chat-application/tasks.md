---
description: "Task list for OpenAI Chat Application with Cloud SQL integration"
---

# Tasks: OpenAI Chat Application

**Input**: Constitution v3.0.0 - OpenAI API-based Multi-turn Conversation System  
**Prerequisites**: GCP Cloud SQL instance, OpenAI API key, existing backend structure

**Tests**: Tests are OPTIONAL - include basic integration tests for critical paths

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Backend: `meridian-backend/`
- Database: `meridian-backend/database/`
- API: `meridian-backend/api/` or endpoints in `meridian-backend/server.py`
- Services: `meridian-backend/services/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create database directory structure in meridian-backend/database/
- [X] T002 Create services directory structure in meridian-backend/services/
- [X] T003 [P] Install required dependencies: openai, google-cloud-sql-connector, asyncpg (or pymysql), sqlalchemy in meridian-backend/requirements.txt
- [X] T004 [P] Configure environment variables documentation in meridian-backend/.env.example

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create GCP Cloud SQL client in meridian-backend/database/cloud_sql_client.py
- [X] T006 [P] Implement database connection pooling in meridian-backend/database/cloud_sql_client.py
- [X] T007 [P] Create database models (SQLAlchemy) for threads and messages in meridian-backend/database/models.py
- [X] T008 Create database migration script for threads table in meridian-backend/database/migrations/001_create_threads.sql
- [X] T009 Create database migration script for messages table in meridian-backend/database/migrations/002_create_messages.sql
- [X] T010 Test Cloud SQL connection with basic query in meridian-backend/database/test_connection.py
- [ ] T011 Verify database schema creation (run migrations) and test CRUD operations
- [X] T012 Create OpenAI service wrapper in meridian-backend/services/openai_service.py
- [X] T013 [P] Configure error handling and logging infrastructure in meridian-backend/server.py
- [X] T014 [P] Setup environment configuration management for DB and OpenAI in meridian-backend/utils/config.py

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Thread Management (Priority: P1) 🎯 MVP

**Goal**: Users can create, list, view, and delete chat threads. Threads are stored in Cloud SQL and displayed in the frontend.

**Independent Test**: 
- Create a thread via POST /api/threads → verify it appears in GET /api/threads
- Delete a thread via DELETE /api/threads/{thread_id} → verify it's removed from list
- Frontend displays thread list and can select threads

### Implementation for User Story 1

- [X] T015 [US1] Create Thread model (Pydantic) in meridian-backend/models/thread.py
- [X] T016 [US1] Create ThreadService with create_thread method in meridian-backend/services/thread_service.py
- [X] T017 [US1] Create ThreadService with list_threads method in meridian-backend/services/thread_service.py
- [X] T018 [US1] Create ThreadService with get_thread method in meridian-backend/services/thread_service.py
- [X] T019 [US1] Create ThreadService with delete_thread method (with cascade delete) in meridian-backend/services/thread_service.py
- [X] T020 [US1] Implement POST /api/threads endpoint in meridian-backend/server.py
- [X] T021 [US1] Implement GET /api/threads endpoint in meridian-backend/server.py
- [X] T022 [US1] Implement GET /api/threads/{thread_id} endpoint in meridian-backend/server.py
- [X] T023 [US1] Implement DELETE /api/threads/{thread_id} endpoint in meridian-backend/server.py
- [X] T024 [US1] Add request/response models with Field descriptions for thread endpoints in meridian-backend/server.py
- [X] T025 [US1] Add error handling for thread not found (404) in meridian-backend/server.py
- [X] T026 [US1] Add logging for thread operations in meridian-backend/services/thread_service.py

**Checkpoint**: At this point, User Story 1 should be fully functional - threads can be created, listed, viewed, and deleted via API

---

## Phase 4: User Story 2 - Conversation History (Priority: P2)

**Goal**: Users can view the complete conversation history for any thread. Messages are retrieved from Cloud SQL and displayed chronologically in the frontend.

**Independent Test**: 
- Create a thread
- Send messages to the thread (via US3)
- Retrieve messages via GET /api/threads/{thread_id}/messages → verify chronological order
- Frontend displays messages in correct order when thread is selected

### Implementation for User Story 2

- [X] T027 [US2] Create Message model (Pydantic) in meridian-backend/models/message.py
- [X] T028 [US2] Create MessageService with get_messages_by_thread method in meridian-backend/services/message_service.py
- [X] T029 [US2] Implement GET /api/threads/{thread_id}/messages endpoint in meridian-backend/server.py
- [X] T030 [US2] Add message ordering by timestamp (ascending) in meridian-backend/services/message_service.py
- [X] T031 [US2] Add request/response models with Field descriptions for messages endpoint in meridian-backend/server.py
- [X] T032 [US2] Add error handling for thread not found (404) in message retrieval in meridian-backend/server.py
- [X] T033 [US2] Add logging for message retrieval operations in meridian-backend/services/message_service.py

**Checkpoint**: At this point, User Stories 1 AND 2 should both work - threads can be managed and conversation history can be retrieved

---

## Phase 5: User Story 3 - Chat Response API (Priority: P3)

**Goal**: Users can send messages to a thread and receive LLM responses. Messages are saved to the database and conversation context is maintained.

**Independent Test**: 
- Create a thread
- Send message via POST /api/chat → verify user message saved, assistant response received and saved
- Send follow-up message → verify conversation context maintained (assistant remembers previous messages)
- Frontend displays both user and assistant messages in real-time

### Implementation for User Story 3

- [X] T034 [US3] Create ChatRequest and ChatResponse models (Pydantic) in meridian-backend/models/chat.py
- [X] T035 [US3] Implement save_user_message method in meridian-backend/services/message_service.py
- [X] T036 [US3] Implement save_assistant_message method in meridian-backend/services/message_service.py
- [X] T037 [US3] Implement get_conversation_context method (retrieve last N messages) in meridian-backend/services/message_service.py
- [X] T038 [US3] Implement chat_with_openai method with conversation context in meridian-backend/services/openai_service.py
- [X] T039 [US3] Create ChatService orchestrating message save → OpenAI call → response save in meridian-backend/services/chat_service.py
- [X] T040 [US3] Implement POST /api/chat endpoint in meridian-backend/server.py
- [X] T041 [US3] Add conversation context limit (last 20 messages) in meridian-backend/services/chat_service.py
- [X] T042 [US3] Add error handling for OpenAI API errors (502) in meridian-backend/services/openai_service.py
- [X] T043 [US3] Add error handling for database errors (503) in meridian-backend/services/chat_service.py
- [X] T044 [US3] Add request/response models with Field descriptions for chat endpoint in meridian-backend/server.py
- [X] T045 [US3] Add logging for chat operations in meridian-backend/services/chat_service.py
- [X] T046 [US3] Update thread updated_at timestamp on new message in meridian-backend/services/chat_service.py

**Checkpoint**: At this point, all user stories should work - complete chat flow from thread creation to sending messages and receiving responses

---

## Phase 6: User Story 4 - Frontend Integration (Priority: P4)

**Goal**: Frontend displays real data from backend APIs. No template/mock data. All UI components interact with actual backend endpoints.

**Independent Test**: 
- Frontend thread list shows threads from GET /api/threads
- Clicking a thread loads messages from GET /api/threads/{thread_id}/messages
- Sending a message calls POST /api/chat and displays response
- Creating a thread calls POST /api/threads and appears in list
- Deleting a thread calls DELETE /api/threads/{thread_id} and removes from list

### Implementation for User Story 4

- [X] T047 [US4] Update frontend thread list component to call GET /api/threads in frontend source
- [X] T048 [US4] Update frontend thread selection to call GET /api/threads/{thread_id}/messages in frontend source
- [X] T049 [US4] Update frontend message sending to call POST /api/chat in frontend source
- [X] T050 [US4] Update frontend thread creation to call POST /api/threads in frontend source
- [X] T051 [US4] Update frontend thread deletion to call DELETE /api/threads/{thread_id} in frontend source
- [X] T052 [US4] Add error handling and user-friendly error messages in frontend components
- [X] T053 [US4] Add loading states during API calls in frontend components
- [X] T054 [US4] Remove all template/mock data from frontend components
- [X] T055 [US4] Verify message ordering (chronological) in frontend display
- [X] T056 [US4] Add real-time message display after sending (update UI immediately)

**Checkpoint**: Frontend is fully functional with real backend integration - no mock data

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T057 [P] Create architectural guideline document in docs/architecture.md
- [ ] T058 [P] Add API documentation with examples in docs/api_reference.md
- [ ] T059 [P] Code cleanup and refactoring across all services
- [ ] T060 [P] Add connection retry logic for Cloud SQL in meridian-backend/database/cloud_sql_client.py
- [ ] T061 [P] Add database transaction management for atomic operations in meridian-backend/services/
- [ ] T062 [P] Performance optimization: Add database indexes verification in meridian-backend/database/migrations/
- [ ] T063 [P] Security hardening: Validate all inputs, sanitize outputs in meridian-backend/server.py
- [ ] T064 [P] Add health check endpoint that verifies database connectivity in meridian-backend/server.py
- [ ] T065 [P] Add request ID tracking for logging correlation in meridian-backend/server.py
- [ ] T066 [P] Add rate limiting for OpenAI API calls in meridian-backend/services/openai_service.py
- [ ] T067 [P] Add conversation length limits and truncation logic in meridian-backend/services/chat_service.py

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-6)**: All depend on Foundational phase completion
  - User stories can then proceed sequentially in priority order (P1 → P2 → P3 → P4)
  - US2 depends on US1 (needs threads to exist)
  - US3 depends on US1 and US2 (needs threads and message storage)
  - US4 depends on US1, US2, US3 (needs all APIs working)
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Depends on US1 (needs threads table and thread management)
- **User Story 3 (P3)**: Depends on US1 and US2 (needs threads, messages table, and message retrieval)
- **User Story 4 (P4)**: Depends on US1, US2, US3 (needs all APIs functional)

### Within Each User Story

- Models before services
- Services before endpoints
- Core implementation before integration
- Story complete before moving to next priority

### Parallel Opportunities

- Setup tasks T003, T004 can run in parallel
- Foundational tasks T006, T007, T013, T014 can run in parallel (within Phase 2)
- Once Foundational phase completes, user stories must proceed sequentially due to dependencies
- Polish phase tasks T057-T067 can mostly run in parallel

---

## Parallel Example: Foundational Phase

```bash
# Launch foundational tasks in parallel:
Task: "Implement database connection pooling in meridian-backend/database/cloud_sql_client.py"
Task: "Create database models (SQLAlchemy) for threads and messages in meridian-backend/database/models.py"
Task: "Configure error handling and logging infrastructure in meridian-backend/server.py"
Task: "Setup environment configuration management for DB and OpenAI in meridian-backend/utils/config.py"
```

---

## Implementation Strategy

### MVP First (User Stories 1-3 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1 (Thread Management)
4. Complete Phase 4: User Story 2 (Conversation History)
5. Complete Phase 5: User Story 3 (Chat Response API)
6. **STOP and VALIDATE**: Test all APIs independently via curl/Postman
7. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (Thread Management MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo (Conversation History)
4. Add User Story 3 → Test independently → Deploy/Demo (Chat Functionality)
5. Add User Story 4 → Test independently → Deploy/Demo (Full Frontend Integration)
6. Each story adds value without breaking previous stories

### Sequential Strategy (Required Due to Dependencies)

With the current dependency structure:
1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Complete User Story 1 (Thread Management)
   - Then User Story 2 (Conversation History)
   - Then User Story 3 (Chat Response API)
   - Finally User Story 4 (Frontend Integration)
3. Stories build on each other incrementally

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Test Cloud SQL connection before proceeding with database operations
- Verify OpenAI API key is configured before implementing chat functionality
- All database operations must use parameterized queries to prevent SQL injection
- Frontend must remove all mock/template data before completion

---

## Task Summary

- **Total Tasks**: 67
- **Phase 1 (Setup)**: 4 tasks
- **Phase 2 (Foundational)**: 10 tasks
- **Phase 3 (US1 - Thread Management)**: 12 tasks
- **Phase 4 (US2 - Conversation History)**: 7 tasks
- **Phase 5 (US3 - Chat Response API)**: 13 tasks
- **Phase 6 (US4 - Frontend Integration)**: 10 tasks
- **Phase 7 (Polish)**: 11 tasks

**Parallel Opportunities**: 
- Setup: 2 tasks
- Foundational: 4 tasks
- Polish: 11 tasks

**Suggested MVP Scope**: Phases 1-5 (Setup + Foundational + US1-3) = 46 tasks
- This delivers a fully functional backend API for chat functionality
- Frontend integration (US4) can be added as a follow-up

**Independent Test Criteria**:
- US1: Thread CRUD operations work via API
- US2: Message retrieval works for existing threads
- US3: Chat flow works end-to-end (send message → get response → save both)
- US4: Frontend displays real data and interacts with all APIs

