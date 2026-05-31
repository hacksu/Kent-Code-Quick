// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
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
vi.mock('$lib/components/Timer.svelte', () => ({
	default: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

function fireSocketEvent(event: string, ...args: unknown[]) {
	for (const cb of listeners[event] ?? []) cb(...args);
}

beforeEach(() => {
	mockGoto.mockClear();
	mockSocket.emit.mockClear();
	mockFetch.mockClear();
	Object.keys(listeners).forEach((k) => delete listeners[k]);
});

import Page from './+page.svelte';

describe('Admin page - auth gate', () => {
	it('redirects to Discord OAuth when not authenticated', async () => {
		mockFetch.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) });
		render(Page);
		await waitFor(() => expect(mockGoto).toHaveBeenCalledWith('/auth/discord?next=/admin'));
	});

	it('redirects when authenticated but not admin', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: async () => ({ discord_id: '1', discord_username: 'User', is_admin: false }),
		});
		render(Page);
		await waitFor(() => expect(mockGoto).toHaveBeenCalledWith('/auth/discord?next=/admin'));
	});
});

describe('Admin page - dashboard', () => {
	beforeEach(() => {
		mockFetch.mockResolvedValue({
			ok: true,
			status: 200,
			json: async () => ({ discord_id: '1', discord_username: 'Admin', is_admin: true }),
		});
	});

	it('shows admin username after auth', async () => {
		const { container } = render(Page);
		await waitFor(() => expect(container.textContent).toContain('Admin'));
	});

	it('shows Create Game button', async () => {
		const { container } = render(Page);
		await waitFor(() =>
			expect(container.querySelector('[data-testid="create-game-btn"]')).toBeTruthy()
		);
	});

	it('shows Start Game button when game is waiting', async () => {
		const { container } = render(Page);
		await waitFor(() =>
			expect(container.querySelector('[data-testid="create-game-btn"]')).toBeTruthy()
		);
		fireSocketEvent('game_state', {
			status: 'waiting',
			duration_ms: 2700000,
			lobby_count: 3,
			started_at: null,
			ended_at: null,
			participants: {},
		});
		flushSync();
		expect(container.querySelector('[data-testid="start-game-btn"]')).toBeTruthy();
	});

	it('emits start_game when Start Game is clicked', async () => {
		const { container } = render(Page);
		await waitFor(() =>
			expect(container.querySelector('[data-testid="create-game-btn"]')).toBeTruthy()
		);
		fireSocketEvent('game_state', {
			status: 'waiting',
			duration_ms: 2700000,
			lobby_count: 1,
			started_at: null,
			ended_at: null,
			participants: {},
		});
		flushSync();
		await fireEvent.click(container.querySelector('[data-testid="start-game-btn"]')!);
		expect(mockSocket.emit).toHaveBeenCalledWith('start_game', {});
	});
});
