import { describe, it, expect, beforeEach, vi } from 'vitest';
import { storage, STORAGE_KEYS } from './storage';

describe('storage', () => {
  beforeEach(() => {
    // Clear localStorage before each test
    localStorage.clear();
  });

  describe('get', () => {
    it('returns null for non-existent key', () => {
      const result = storage.get('non-existent-key');
      expect(result).toBeNull();
    });

    it('retrieves stored value', () => {
      storage.set('test-key', { name: 'test', value: 123 });
      const result = storage.get<{ name: string; value: number }>('test-key');
      
      expect(result).toEqual({ name: 'test', value: 123 });
    });

    it('returns null when window is undefined (SSR)', () => {
      const originalWindow = global.window;
      // @ts-expect-error - intentionally removing window for SSR test
      delete global.window;
      
      const result = storage.get('test-key');
      expect(result).toBeNull();
      
      global.window = originalWindow;
    });

    it('handles invalid JSON gracefully', () => {
      localStorage.setItem('invalid-json', 'not valid json{');
      const result = storage.get('invalid-json');
      expect(result).toBeNull();
    });
  });

  describe('set', () => {
    it('stores a value', () => {
      storage.set('test-key', { data: 'value' });
      const stored = localStorage.getItem('test-key');
      expect(stored).toBeTruthy();
      expect(JSON.parse(stored!)).toEqual({ data: 'value' });
    });

    it('stores primitive values', () => {
      storage.set('string-key', 'string-value');
      storage.set('number-key', 42);
      storage.set('boolean-key', true);
      
      expect(storage.get<string>('string-key')).toBe('string-value');
      expect(storage.get<number>('number-key')).toBe(42);
      expect(storage.get<boolean>('boolean-key')).toBe(true);
    });

    it('does nothing when window is undefined (SSR)', () => {
      const originalWindow = global.window;
      // @ts-expect-error - intentionally removing window for SSR test
      delete global.window;
      
      // Should not throw
      storage.set('test-key', 'value');
      
      global.window = originalWindow;
    });

    it('handles storage quota errors gracefully', () => {
      // Mock localStorage.setItem to throw quota error
      const originalSetItem = localStorage.setItem;
      localStorage.setItem = vi.fn(() => {
        throw new DOMException('QuotaExceededError');
      });
      
      // Should not throw
      expect(() => storage.set('test-key', 'value')).not.toThrow();
      
      localStorage.setItem = originalSetItem;
    });
  });

  describe('remove', () => {
    it('removes a stored value', () => {
      storage.set('test-key', 'value');
      storage.remove('test-key');
      
      expect(storage.get('test-key')).toBeNull();
    });

    it('does nothing when window is undefined (SSR)', () => {
      const originalWindow = global.window;
      // @ts-expect-error - intentionally removing window for SSR test
      delete global.window;
      
      // Should not throw
      storage.remove('test-key');
      
      global.window = originalWindow;
    });
  });

  describe('clear', () => {
    it('clears all storage keys', () => {
      storage.set(STORAGE_KEYS.THEME, 'dark');
      storage.set(STORAGE_KEYS.USER, { id: '1' });
      storage.set(STORAGE_KEYS.TOKEN, 'token123');
      
      storage.clear();
      
      expect(storage.get(STORAGE_KEYS.THEME)).toBeNull();
      expect(storage.get(STORAGE_KEYS.USER)).toBeNull();
      expect(storage.get(STORAGE_KEYS.TOKEN)).toBeNull();
    });

    it('does nothing when window is undefined (SSR)', () => {
      const originalWindow = global.window;
      // @ts-expect-error - intentionally removing window for SSR test
      delete global.window;
      
      // Should not throw
      storage.clear();
      
      global.window = originalWindow;
    });
  });
});

