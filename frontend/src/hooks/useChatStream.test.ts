import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useChatStream } from './useChatStream';

describe('useChatStream telemetry', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('calculates TTFB on first TEXT event after starting stream', () => {
    const { result } = renderHook(() => useChatStream({ apiUrl: 'http://localhost' }));

    act(() => {
      result.current.startStream('Hello');
    });

    // Advance time to simulate network latency
    act(() => {
      vi.advanceTimersByTime(250);
    });

    // Fire ROUTER event (should not set TTFB)
    act(() => {
      result.current.handleStreamEvent({ type: 'ROUTER', intent: 'CODER' });
    });

    expect(result.current.ttfb).toBeNull();

    // Fire TEXT event (should set TTFB)
    act(() => {
      vi.advanceTimersByTime(100); // Total 350ms
      result.current.handleStreamEvent({ type: 'TEXT', content: 'Hi' });
    });

    expect(result.current.ttfb).toBe(350);
    expect(result.current.isLoading).toBe(false);
  });

  it('updates process logs appropriately based on events', () => {
    const { result } = renderHook(() => useChatStream({ apiUrl: 'http://localhost' }));

    act(() => {
      result.current.startStream('Hello');
    });

    expect(result.current.processLogs[0].message).toBe('Initiating neural uplink...');

    act(() => {
      result.current.handleStreamEvent({ type: 'ROUTER', intent: 'CODER' });
    });

    expect(result.current.processLogs[1].message).toBe('Intent identified: CODER');
  });
});
