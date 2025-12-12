import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { InputBar } from './InputBar';

describe('InputBar', () => {
  it('renders textarea input', () => {
    const onSend = vi.fn();
    render(<InputBar onSend={onSend} />);
    
    const textarea = screen.getByLabelText('Message input');
    expect(textarea).toBeInTheDocument();
  });

  it('calls onSend when send button is clicked', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<InputBar onSend={onSend} />);
    
    const textarea = screen.getByLabelText('Message input');
    const sendButton = screen.getByLabelText('Send message');
    
    await user.type(textarea, 'Hello, world!');
    await user.click(sendButton);
    
    expect(onSend).toHaveBeenCalledWith('Hello, world!');
    expect(textarea).toHaveValue('');
  });

  it('calls onSend when Enter is pressed', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<InputBar onSend={onSend} />);
    
    const textarea = screen.getByLabelText('Message input');
    await user.type(textarea, 'Test message{Enter}');
    
    expect(onSend).toHaveBeenCalledWith('Test message');
  });

  it('does not send when Shift+Enter is pressed', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<InputBar onSend={onSend} />);
    
    const textarea = screen.getByLabelText('Message input');
    await user.type(textarea, 'Test message{Shift>}{Enter}{/Shift}');
    
    expect(onSend).not.toHaveBeenCalled();
  });

  it('does not send empty messages', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<InputBar onSend={onSend} />);
    
    const sendButton = screen.getByLabelText('Send message');
    await user.click(sendButton);
    
    expect(onSend).not.toHaveBeenCalled();
  });

  it('disables input when disabled prop is true', () => {
    const onSend = vi.fn();
    render(<InputBar onSend={onSend} disabled />);
    
    const textarea = screen.getByLabelText('Message input');
    const sendButton = screen.getByLabelText('Send message');
    
    expect(textarea).toBeDisabled();
    expect(sendButton).toBeDisabled();
  });

  it('does not send when disabled', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<InputBar onSend={onSend} disabled />);
    
    const textarea = screen.getByLabelText('Message input');
    await user.type(textarea, 'Test{Enter}');
    
    expect(onSend).not.toHaveBeenCalled();
  });

  it('trims whitespace from messages', async () => {
    const onSend = vi.fn();
    const user = userEvent.setup();
    render(<InputBar onSend={onSend} />);
    
    const textarea = screen.getByLabelText('Message input');
    await user.type(textarea, '   Test message   {Enter}');
    
    expect(onSend).toHaveBeenCalledWith('Test message');
  });

  it('uses custom placeholder', () => {
    const onSend = vi.fn();
    render(<InputBar onSend={onSend} placeholder="Custom placeholder" />);
    
    const textarea = screen.getByPlaceholderText('Custom placeholder');
    expect(textarea).toBeInTheDocument();
  });
});

