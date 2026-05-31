// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
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
vi.mock('$lib/components/ParticipantCard.svelte', () => ({
	default: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
}));
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

describe('Watch page - auth gate', () => {
	it('redirects to Discord OAuth when not admin', async () => {
		mockFetch.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) });
		render(Page);
		await waitFor(() =>
			expect(mockGoto).toHaveBeenCalledWith('/auth/discord?next=/watch')
		);
	});

	it('redirects when authenticated but not admin', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: async () => ({ discord_id: '1', discord_username: 'User', is_admin: false }),
		});
		render(Page);
		await waitFor(() =>
			expect(mockGoto).toHaveBeenCalledWith('/auth/discord?next=/watch')
		);
	});
});

describe('Watch page - live view', () => {
	beforeEach(() => {
		mockFetch.mockResolvedValue({
			ok: true,
			status: 200,
			json: async () => ({ discord_id: '1', discord_username: 'Admin', is_admin: true }),
		});
	});

	it('shows participant cards from game_state', async () => {
		const { container } = render(Page);
		await waitFor(() => expect(container.textContent).not.toMatch(/checking/i));
		fireSocketEvent('game_state', {
			status: 'active',
			duration_ms: 2700000,
			started_at: Date.now() / 1000,
			ended_at: null,
			lobby_count: 0,
			participants: {
				tok1: {
					id: '1',
					name: 'Alice',
					html: '',
					css: '',
					penalty_ms: 0,
					tab_out_count: 0,
					copy_attempt_count: 0,
					submitted_at: null,
					final_html: null,
					final_css: null,
				},
				tok2: {
					id: '2',
					name: 'Bob',
					html: '',
					css: '',
					penalty_ms: 5000,
					tab_out_count: 1,
					copy_attempt_count: 0,
					submitted_at: null,
					final_html: null,
					final_css: null,
				},
			},
		});
		flushSync();
		expect(container.querySelectorAll('[data-participant]').length).toBe(2);
	});

	it('shows End Game button during active game', async () => {
		const { container } = render(Page);
		await waitFor(() => expect(container.textContent).not.toMatch(/checking/i));
		fireSocketEvent('game_state', {
			status: 'active',
			duration_ms: 2700000,
			started_at: Date.now() / 1000,
			ended_at: null,
			lobby_count: 0,
			participants: {},
		});
		flushSync();
		expect(container.querySelector('[data-testid="end-game-btn"]')).toBeTruthy();
	});
});
