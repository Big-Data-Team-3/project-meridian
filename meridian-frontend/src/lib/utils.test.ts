import { describe, it, expect, vi } from 'vitest';
import { cn, formatDate, debounce } from './utils';

describe('cn', () => {
  it('combines class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('filters out falsy values', () => {
    expect(cn('foo', false, 'bar', null, undefined)).toBe('foo bar');
  });

  it('handles empty input', () => {
    expect(cn()).toBe('');
  });
});

describe('formatDate', () => {
  it('formats a date string', () => {
    const date = new Date('2024-12-19T10:30:00');
    const formatted = formatDate(date);
    expect(formatted).toMatch(/Dec/);
    expect(formatted).toMatch(/19/);
  });

  it('formats a Date object', () => {
    const date = new Date('2024-12-19T10:30:00');
    const formatted = formatDate(date);
    expect(typeof formatted).toBe('string');
  });
});

describe('debounce', () => {
  it('delays function execution', async () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);
    
    debounced();
    expect(fn).not.toHaveBeenCalled();
    
    await new Promise((resolve) => setTimeout(resolve, 150));
    expect(fn).toHaveBeenCalledTimes(1);
  });

  it('cancels previous calls', async () => {
    const fn = vi.fn();
    const debounced = debounce(fn, 100);
    
    debounced();
    debounced();
    debounced();
    
    await new Promise((resolve) => setTimeout(resolve, 150));
    expect(fn).toHaveBeenCalledTimes(1);
  });
});

