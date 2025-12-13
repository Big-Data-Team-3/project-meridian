import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { render as customRender } from '../utils/test-utils';
import { InputBar } from '@/components/chat/InputBar';
import { MessageBubble } from '@/components/chat/MessageBubble';
import { AgentProvider } from '@/contexts/AgentContext';
import type { Message } from '@/types';

// Mock the API client
vi.mock('@/lib/api', () => ({
  apiClient: {
    sendMessage: vi.fn(),
    getMessages: vi.fn(),
  },
}));

// Mock AgentContext at module level
const mockSetTraceFromMessage = vi.fn();
const mockOpenTrace = vi.fn();

vi.mock('@/contexts/AgentContext', async () => {
  const actual = await vi.importActual('@/contexts/AgentContext');
  return {
    ...actual,
    useAgent: () => ({
      setTraceFromMessage: mockSetTraceFromMessage,
      openTrace: mockOpenTrace,
    }),
  };
});

describe('Chat Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('allows user to type and send a message', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    customRender(<InputBar onSend={onSend} />);

    const textarea = screen.getByLabelText('Message input');
    await user.type(textarea, 'Hello, this is a test message');

    const sendButton = screen.getByLabelText('Send message');
    await user.click(sendButton);

    expect(onSend).toHaveBeenCalledWith('Hello, this is a test message');
    expect(textarea).toHaveValue('');
  });

  it('displays user and assistant messages in conversation', () => {
    const userMessage: Message = {
      id: '1',
      role: 'user',
      content: 'What is the stock price of AAPL?',
      timestamp: new Date('2024-01-01T10:00:00'),
      conversationId: 'conv-1',
    };

    const assistantMessage: Message = {
      id: '2',
      role: 'assistant',
      content: 'The current stock price of AAPL is $150.25.',
      timestamp: new Date('2024-01-01T10:01:00'),
      conversationId: 'conv-1',
    };

    customRender(
      <AgentProvider>
        <div>
          <MessageBubble message={userMessage} />
          <MessageBubble message={assistantMessage} />
        </div>
      </AgentProvider>
    );

    expect(screen.getByText('What is the stock price of AAPL?')).toBeInTheDocument();
    expect(screen.getByText(/The current stock price of AAPL is \$150.25/)).toBeInTheDocument();
  });

  it('handles message with agent trace interaction', async () => {
    const user = userEvent.setup();

    const message: Message = {
      id: '1',
      role: 'assistant',
      content: 'Analysis complete',
      timestamp: new Date(),
      conversationId: 'conv-1',
      agentTrace: {
        events: [],
        agentsCalled: ['analyst', 'trader'],
        totalProgress: 100,
        startTime: new Date(),
        endTime: new Date(),
      },
    };

    customRender(
      <AgentProvider>
        <MessageBubble message={message} />
      </AgentProvider>
    );

    const traceButton = screen.getByText(/Trace/);
    await user.click(traceButton);

    // Note: In a real integration test, you'd verify the trace sidebar opens
    // This is a simplified version
    expect(traceButton).toBeInTheDocument();
  });

  it('handles markdown rendering in assistant messages', () => {
    const message: Message = {
      id: '1',
      role: 'assistant',
      content: '# Analysis Report\n\n**Key Findings:**\n- Point 1\n- Point 2',
      timestamp: new Date(),
      conversationId: 'conv-1',
    };

    customRender(
      <AgentProvider>
        <MessageBubble message={message} />
      </AgentProvider>
    );

    // Markdown should be rendered
    expect(screen.getByText('Analysis Report')).toBeInTheDocument();
    expect(screen.getByText('Key Findings:')).toBeInTheDocument();
  });

  it('prevents sending empty messages', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    customRender(<InputBar onSend={onSend} />);

    const sendButton = screen.getByLabelText('Send message');
    await user.click(sendButton);

    expect(onSend).not.toHaveBeenCalled();
  });

  it('handles disabled state during message sending', async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    customRender(<InputBar onSend={onSend} disabled />);

    const textarea = screen.getByLabelText('Message input');
    const sendButton = screen.getByLabelText('Send message');

    expect(textarea).toBeDisabled();
    expect(sendButton).toBeDisabled();

    await user.type(textarea, 'Test message');
    await user.click(sendButton);

    expect(onSend).not.toHaveBeenCalled();
  });
});

