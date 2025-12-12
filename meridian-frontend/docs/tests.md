# Frontend Tests

## Commands
- Install deps: `cd meridian-frontend && npm install`
- Unit tests: `npm run test`
- Integration/UI tests (headed UI): `npm run test:ui`
- Coverage: `npm run test:coverage`
- Lint: `npm run lint`

## Coverage Focus
- Hooks (`src/hooks/*`): streaming, auth, conversations.
- Components (`src/components/chat/*`, `src/components/ui/*`): rendering, interaction, accessibility.
- Lib (`src/lib/api.ts`, `src/lib/utils.ts`): request shaping and formatting utilities.

## Integration Notes
- Mock backend/agent APIs via `msw` in `__tests__/utils/setup.ts`.
- Prefer Testing Library queries (`getByRole`, `findByText`) to keep tests user-centric.
- Add snapshots sparingly; verify traces and streaming updates through state assertions.

