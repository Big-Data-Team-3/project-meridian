import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider, useTheme } from './ThemeContext';
import { storage, STORAGE_KEYS } from '@/lib/storage';

// Component to test the hook
function TestComponent() {
  const { theme, toggleTheme, setTheme } = useTheme();
  return (
    <div>
      <div data-testid="theme">{theme}</div>
      <button onClick={toggleTheme}>Toggle</button>
      <button onClick={() => setTheme('dark')}>Set Dark</button>
      <button onClick={() => setTheme('light')}>Set Light</button>
    </div>
  );
}

describe('ThemeContext', () => {
  beforeEach(() => {
    localStorage.clear();
    vi.clearAllMocks();
    
    // Mock window.matchMedia to return dark preference by default
    Object.defineProperty(window, 'matchMedia', {
      writable: true,
      value: vi.fn().mockImplementation((query) => {
        if (query === '(prefers-color-scheme: dark)') {
          return {
            matches: true, // Default to dark theme
            media: query,
            onchange: null,
            addListener: vi.fn(),
            removeListener: vi.fn(),
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn(),
          };
        }
        return {
          matches: false,
          media: query,
          onchange: null,
          addListener: vi.fn(),
          removeListener: vi.fn(),
          addEventListener: vi.fn(),
          removeEventListener: vi.fn(),
          dispatchEvent: vi.fn(),
        };
      }),
    });
  });

  it('provides default dark theme', async () => {
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    // Wait for provider to mount and theme to be initialized
    await waitFor(() => {
      const themeDisplay = screen.getByTestId('theme');
      expect(themeDisplay).toHaveTextContent('dark');
    });
  });

  it('loads theme from localStorage', async () => {
    storage.set(STORAGE_KEYS.THEME, 'light');
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    // Wait for useEffect to run and theme to be applied
    await waitFor(() => {
      expect(document.documentElement.getAttribute('data-theme')).toBe('light');
    });
  });

  it('toggles theme between dark and light', async () => {
    const user = userEvent.setup();
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    // Wait for provider to mount and theme to be initialized
    await waitFor(() => {
      const themeDisplay = screen.getByTestId('theme');
      expect(themeDisplay).toHaveTextContent('dark');
    });

    const themeDisplay = screen.getByTestId('theme');
    const toggleButton = screen.getByText('Toggle');

    // Toggle to light
    await user.click(toggleButton);
    expect(themeDisplay).toHaveTextContent('light');

    // Toggle back to dark
    await user.click(toggleButton);
    expect(themeDisplay).toHaveTextContent('dark');
  });

  it('sets theme explicitly', async () => {
    const user = userEvent.setup();
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    // Wait for provider to mount - use findBy which waits for the element
    const themeDisplay = await screen.findByTestId('theme');
    const setLightButton = await screen.findByText('Set Light');

    await user.click(setLightButton);
    expect(themeDisplay).toHaveTextContent('light');
    expect(storage.get(STORAGE_KEYS.THEME)).toBe('light');
  });

  it('saves theme to localStorage', async () => {
    const user = userEvent.setup();
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    // Wait for provider to mount - use findBy which waits for the element
    const setLightButton = await screen.findByText('Set Light');
    await user.click(setLightButton);

    expect(storage.get(STORAGE_KEYS.THEME)).toBe('light');
  });

  it('updates data-theme attribute on document', async () => {
    const user = userEvent.setup();
    
    render(
      <ThemeProvider>
        <TestComponent />
      </ThemeProvider>
    );

    // Wait for provider to mount - use findBy which waits for the element
    const setLightButton = await screen.findByText('Set Light');
    await user.click(setLightButton);

    expect(document.documentElement.getAttribute('data-theme')).toBe('light');
  });

  it('throws error when used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    expect(() => {
      render(<TestComponent />);
    }).toThrow('useTheme must be used within a ThemeProvider');

    consoleSpy.mockRestore();
  });
});

