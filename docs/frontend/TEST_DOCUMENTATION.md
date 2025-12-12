# Frontend Test Documentation

This document provides an overview of all tests in the meridian-frontend project, organized by category and purpose.

## Table of Contents

- [Running Tests](#running-tests)
- [Test Structure](#test-structure)
- [Unit Tests](#unit-tests)
- [Component Tests](#component-tests)
- [Hook Tests](#hook-tests)
- [Integration Tests](#integration-tests)
- [Test Utilities](#test-utilities)

---

## Running Tests

### Basic Commands

```bash
# Run all tests in watch mode
npm test

# Run tests with UI (interactive)
npm run test:ui

# Run tests with coverage report
npm run test:coverage

# Run tests once (no watch mode)
npm test -- --run
```

### Test Configuration

- **Test Runner**: Vitest
- **Test Environment**: jsdom (for browser-like environment)
- **Setup File**: `__tests__/utils/setup.ts`
- **Coverage Provider**: v8
- **Coverage Reports**: text, JSON, HTML

---

## Test Structure

Tests are organized into three main categories:

1. **Unit Tests** (`src/**/*.test.ts`) - Test individual functions and utilities
2. **Component Tests** (`src/**/*.test.tsx`) - Test React components
3. **Integration Tests** (`__tests__/integration/*.test.tsx`) - Test component interactions

---

## Unit Tests

### 1. `src/lib/utils.test.ts`

**Purpose**: Tests utility functions used throughout the application.

**Test Coverage**:
- ✅ `cn()` - Class name utility
  - Combines multiple class names
  - Filters out falsy values (null, undefined, false)
  - Handles empty input
  
- ✅ `formatDate()` - Date formatting
  - Formats date strings
  - Formats Date objects
  - Returns string output
  
- ✅ `debounce()` - Function debouncing
  - Delays function execution
  - Cancels previous calls when called multiple times
  - Useful for search inputs and API calls

**Key Features**:
- Pure function testing (no side effects)
- Edge case handling (null, undefined, empty values)

---

### 2. `src/lib/storage.test.ts`

**Purpose**: Tests localStorage wrapper utility.

**Test Coverage**:
- ✅ `storage.get()` - Retrieve values
  - Returns null for non-existent keys
  - Retrieves stored values correctly
  - Handles SSR (returns null when window is undefined)
  - Handles invalid JSON gracefully
  
- ✅ `storage.set()` - Store values
  - Stores objects and primitives
  - Handles string, number, boolean values
  - Properly serializes to JSON
  
- ✅ `storage.remove()` - Remove values
  - Removes specified keys
  - Handles non-existent keys gracefully
  
- ✅ `storage.clear()` - Clear all storage
  - Removes all stored values

**Key Features**:
- SSR-safe (works without window object)
- Error handling for invalid JSON
- Type-safe with TypeScript generics

---

### 3. `src/lib/api.test.ts`

**Purpose**: Tests API client functionality.

**Test Coverage**:
- ✅ `setToken()` - Token management
  - Stores token in localStorage
  - Removes token when set to null
  
- ✅ `healthCheck()` - Health check endpoint
  - Makes GET request to `/api/health`
  - Includes proper headers
  
- ✅ `loginWithGoogle()` - Google authentication
  - Sends POST request with credential
  - Returns auth token and user data
  
- ✅ `sendMessage()` - Send chat messages
  - Sends POST request with message and thread_id
  - Returns error when conversationId is missing
  
- ✅ `getConversations()` - Fetch conversations
  - Makes GET request to `/api/threads`
  
- ✅ `getMessages()` - Fetch messages
  - Makes GET request to `/api/threads/{id}/messages`
  
- ✅ `createConversation()` - Create new conversation
  - Sends POST request to create thread
  
- ✅ `deleteConversation()` - Delete conversation
  - Sends DELETE request
  
- ✅ Error handling
  - Handles 401 unauthorized (clears token)
  - Handles network errors
  - Handles invalid JSON responses
  
- ✅ Authorization
  - Includes Authorization header when token is set

**Key Features**:
- Mocked fetch API
- Comprehensive error handling tests
- Token management verification

---

## Component Tests

### 4. `src/components/ui/Input.test.tsx`

**Purpose**: Tests the Input component (form input field).

**Test Coverage**:
- ✅ Rendering
  - Renders input field
  - Renders with label
  
- ✅ Error handling
  - Displays error message
  - Applies error styles (border-error class)
  - Sets aria-invalid attribute
  
- ✅ User interactions
  - Calls onChange when input value changes
  
- ✅ States
  - Handles disabled state
  
- ✅ Accessibility
  - Associates label with input using htmlFor

**Key Features**:
- Accessible form inputs
- Error state handling
- User event simulation

---

### 5. `src/components/ui/Button.test.tsx`

**Purpose**: Tests the Button component.

**Test Coverage**:
- ✅ Rendering
  - Renders with children text
  
- ✅ User interactions
  - Calls onClick when clicked
  
- ✅ States
  - Is disabled when disabled prop is true
  
- ✅ Styling
  - Applies variant styles (primary, secondary)
  - Applies size styles (sm, lg)

**Key Features**:
- Multiple variants and sizes
- Click event handling
- Disabled state

---

### 6. `src/components/chat/InputBar.test.tsx`

**Purpose**: Tests the chat input bar component.

**Test Coverage**:
- ✅ Rendering
  - Renders textarea input
  
- ✅ Sending messages
  - Calls onSend when send button is clicked
  - Calls onSend when Enter is pressed
  - Clears input after sending
  
- ✅ Keyboard shortcuts
  - Does not send when Shift+Enter is pressed (allows new lines)
  
- ✅ States
  - Handles disabled state during message sending
  - Prevents sending empty messages
  
- ✅ Character limits
  - Enforces maximum character limit

**Key Features**:
- Keyboard interaction testing
- User event simulation
- Edge case handling (empty messages, disabled state)

---

## Hook Tests

### 7. `src/hooks/useChat.test.tsx`

**Purpose**: Tests the useChat hook for chat functionality.

**Test Coverage**:
- ✅ Initial state
  - Returns empty messages when conversationId is null
  - Does not fetch when not authenticated
  
- ✅ Fetching messages
  - Fetches messages for a conversation
  - Handles messages with agent trace
  - Handles messages with agent analysis
  
- ✅ Sending messages
  - Sends a message and adds optimistic update
  - Sets isSending state during message send
  - Handles send message error
  
- ✅ State management
  - Updates messages list correctly
  - Manages loading states

**Key Features**:
- React Query integration
- Optimistic updates
- Error handling
- Authentication checks

---

## Context Tests

### 8. `src/contexts/ThemeContext.test.tsx`

**Purpose**: Tests the theme context provider and hook.

**Test Coverage**:
- ✅ Default theme
  - Provides default dark theme
  - Loads theme from localStorage
  
- ✅ Theme switching
  - Toggles theme between dark and light
  - Sets theme explicitly (dark/light)
  
- ✅ Persistence
  - Saves theme to localStorage
  - Updates data-theme attribute on document
  
- ✅ Error handling
  - Throws error when used outside provider

**Key Features**:
- System preference detection (mocked in tests)
- localStorage persistence
- Document attribute updates
- Provider validation

---

## Integration Tests

### 9. `__tests__/integration/chat.test.tsx`

**Purpose**: Tests chat functionality end-to-end.

**Test Coverage**:
- ✅ Message sending
  - Allows user to type and send a message
  
- ✅ Message display
  - Displays user and assistant messages in conversation
  - Handles markdown rendering in assistant messages
  
- ✅ Agent trace interaction
  - Handles message with agent trace interaction
  - Opens trace sidebar when trace button is clicked
  
- ✅ Input validation
  - Prevents sending empty messages
  - Handles disabled state during message sending

**Key Features**:
- Full component integration
- Mocked API and context
- User interaction flows
- Markdown rendering verification

---

### 10. `__tests__/integration/auth.test.tsx`

**Purpose**: Tests authentication flow.

**Test Coverage**:
- ✅ Authentication status
  - Renders authentication status
  - Has login button
  - Has register button
  - Has logout button

**Note**: These tests serve as examples of integration test structure. Full implementation would require proper API mocking setup.

---

## Test Utilities

### `__tests__/utils/setup.ts`

**Purpose**: Global test setup file (runs before all tests).

**Common Setup**:
- Mock implementations
- Global mocks (window, navigator, etc.)
- Test environment configuration

### `__tests__/utils/test-utils.tsx`

**Purpose**: Custom render utilities for testing.

**Features**:
- Wrapper components (ThemeProvider, QueryClient, etc.)
- Custom render function with providers
- Reusable test helpers

---

## Test Best Practices

### 1. **Use Descriptive Test Names**
```typescript
// ✅ Good
it('calls onSend when send button is clicked', async () => {
  // ...
});

// ❌ Bad
it('works', () => {
  // ...
});
```

### 2. **Test User Behavior, Not Implementation**
```typescript
// ✅ Good - Tests what user sees
expect(screen.getByText('Hello')).toBeInTheDocument();

// ❌ Bad - Tests implementation details
expect(component.state.message).toBe('Hello');
```

### 3. **Use Appropriate Queries**
- `getByRole` - For accessible elements
- `getByLabelText` - For form inputs
- `getByText` - For text content
- `getByTestId` - Last resort for complex cases

### 4. **Mock External Dependencies**
```typescript
// Mock API calls
vi.mock('@/lib/api', () => ({
  apiClient: {
    sendMessage: vi.fn(),
  },
}));
```

### 5. **Clean Up After Tests**
```typescript
beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
});
```

---

## Coverage Goals

Current focus areas for test coverage:

- ✅ **Hooks** (`src/hooks/*`) - Streaming, auth, conversations
- ✅ **Components** (`src/components/chat/*`, `src/components/ui/*`) - Rendering, interaction, accessibility
- ✅ **Lib** (`src/lib/api.ts`, `src/lib/utils.ts`) - Request shaping and formatting utilities

---

## Common Issues and Solutions

### Issue: Tests failing due to async operations
**Solution**: Use `waitFor` or `findBy` queries
```typescript
await waitFor(() => {
  expect(screen.getByText('Loaded')).toBeInTheDocument();
});
```

### Issue: Theme tests failing
**Solution**: Mock `window.matchMedia` in `beforeEach`
```typescript
Object.defineProperty(window, 'matchMedia', {
  value: vi.fn().mockImplementation(/* ... */),
});
```

### Issue: Clipboard API not working in tests
**Solution**: Use `Object.defineProperty` to mock navigator.clipboard
```typescript
Object.defineProperty(navigator, 'clipboard', {
  value: { writeText: vi.fn() },
  configurable: true,
});
```

---

## Running Specific Tests

```bash
# Run a specific test file
npm test src/lib/utils.test.ts

# Run tests matching a pattern
npm test -- -t "formatDate"

# Run tests in a specific directory
npm test src/components/ui/
```

---

## Additional Resources

- [Vitest Documentation](https://vitest.dev/)
- [Testing Library Documentation](https://testing-library.com/)
- [React Testing Best Practices](https://kentcdodds.com/blog/common-mistakes-with-react-testing-library)

---

## Test Statistics

- **Total Test Files**: 10
- **Unit Tests**: 3 files
- **Component Tests**: 3 files
- **Hook Tests**: 1 file
- **Context Tests**: 1 file
- **Integration Tests**: 2 files

---

*Last Updated: Based on current codebase structure*

