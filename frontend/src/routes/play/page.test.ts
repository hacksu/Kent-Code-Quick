// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';

const { mockGoto } = vi.hoisted(() => ({ mockGoto: vi.fn() }));
vi.mock('$app/navigation', () => ({ goto: mockGoto }));

const listeners: Record<string, ((...args: unknown[]) => void)[]> = {};
const mockSocket = {
	on: vi.fn((event: string, cb: (...args: unknown[]) => void) => {
		if (!listeners[event]) listeners[event] = [];
		listeners[event].push(cb);
	}),
	emit: vi.fn(),
	connect: vi.fn(),
};
vi.mock('socket.io-client', () => ({ io: () => mockSocket }));

// Mock store - default returns a token
vi.mock('$lib/store', () => ({
	loadToken: vi.fn(() => 'test-token'),
	saveToken: vi.fn(),
	clearToken: vi.fn(),
}));

vi.mock('$lib/components/Editor.svelte', () => ({
	default: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
}));
vi.mock('$lib/components/Preview.svelte', () => ({
	default: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
}));
vi.mock('$lib/components/Timer.svelte', () => ({
	default: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
}));
vi.mock('$lib/components/PenaltyBanner.svelte', () => ({
	default: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
}));

function fireSocketEvent(event: string, ...args: unknown[]) {
	for (const cb of listeners[event] ?? []) cb(...args);
}

beforeEach(() => {
	mockGoto.mockClear();
	mockSocket.emit.mockClear();
	Object.keys(listeners).forEach((k) => delete listeners[k]);
});

import Page from './+page.svelte';

describe('Play page', () => {
	it('redirects to / when no token in localStorage', async () => {
		const storeMock = await import('$lib/store');
		vi.mocked(storeMock.loadToken).mockReturnValueOnce(null);
		render(Page);
		expect(mockGoto).toHaveBeenCalledWith('/');
	});

	it('emits join_game with token on connect', () => {
		render(Page);
		fireSocketEvent('connect');
		expect(mockSocket.emit).toHaveBeenCalledWith('join_game', { token: 'test-token' });
	});

	it('shows submit button when not submitted', () => {
		const { container } = render(Page);
		expect(container.querySelector('.submit-btn')).toBeTruthy();
	});

	it('shows Submitted state after submitted event', () => {
		const { container } = render(Page);
		fireSocketEvent('submitted');
		flushSync();
		expect(container.querySelector('.submit-btn')).toBeNull();
		expect(container.textContent).toMatch(/submitted/i);
	});
});
