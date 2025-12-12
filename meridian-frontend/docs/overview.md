# Meridian Frontend Overview

## Purpose
Next.js 16 UI that renders agent analyses, chat traces, and user interactions for Project Meridian.

## Entry Points
- `src/app/page.tsx`: landing page shell.
- `src/app/chat/page.tsx`: main chat experience.
- `src/components/chat/*`: agent trace timeline, activity bubbles, message list.
- `src/lib/api.ts`: HTTP client for backend/agents services.
- `src/contexts/*`: auth, agent, conversation, and theme contexts.

## State & Data Flow
- React Query caches API calls to backend/agents.
- Auth context coordinates Google sign-in and user state.
- Conversation context syncs chat history and message streaming.

## Dependencies
- Next.js 16, React 19, React Query, TailwindCSS.
- Vitest + Testing Library for unit/integration tests.

## Observability
- Client-side logging routed through browser console; backend errors surfaced via API responses displayed in UI components.

