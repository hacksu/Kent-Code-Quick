// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, waitFor } from '@testing-library/svelte';
import { flushSync } from 'svelte';

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
vi.mock('$lib/components/ParticipantFocus.svelte', () => ({
	default: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
}));
vi.mock('$lib/components/Timer.svelte', () => ({
	default: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

const realLocation = window.location;
let locationMock: { replace: ReturnType<typeof vi.fn>; assign: ReturnType<typeof vi.fn>; href: string; origin: string };

function fireSocketEvent(event: string, ...args: unknown[]) {
	for (const cb of listeners[event] ?? []) cb(...args);
}

function participant(id: string, name: string) {
	return {
		id,
		name,
		html: '',
		css: '',
		js: '',
		penalty_ms: 0,
		tab_out_count: 0,
		copy_attempt_count: 0,
		submitted_at: null,
		final_html: null,
		final_css: null,
		final_js: null,
	};
}

beforeEach(() => {
	mockFetch.mockReset();
	mockSocket.emit.mockClear();
	Object.keys(listeners).forEach((k) => delete listeners[k]);
	locationMock = { replace: vi.fn(), assign: vi.fn(), href: '', origin: 'http://localhost:5001' };
	// @ts-expect-error override jsdom location for assertions
	delete window.location;
	// @ts-expect-error override jsdom location for assertions
	window.location = locationMock;
});

afterEach(() => {
	// @ts-expect-error restore jsdom location
	window.location = realLocation;
});

import Page from './+page.svelte';

describe('Watch page - auth gate', () => {
	it('redirects to / when not authenticated', async () => {
		mockFetch.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) });
		render(Page);
		await waitFor(() => expect(locationMock.replace).toHaveBeenCalledWith('/'));
	});

	it('redirects to / when authenticated but not admin', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: async () => ({ discord_id: '1', discord_username: 'User', is_admin: false }),
		});
		render(Page);
		await waitFor(() => expect(locationMock.replace).toHaveBeenCalledWith('/'));
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

	it('shows a participant card per participant from game_state', async () => {
		const { container } = render(Page);
		await waitFor(() => expect(container.textContent).not.toMatch(/checking/i));
		fireSocketEvent('game_state', {
			status: 'active',
			duration_ms: 2_700_000,
			started_at: Date.now() / 1000,
			ended_at: null,
			lobby_count: 0,
			participants: { tok1: participant('1', 'Alice'), tok2: participant('2', 'Bob') },
		});
		flushSync();
		expect(container.querySelectorAll('[data-participant]').length).toBe(2);
	});

	it('shows the End Game button during an active game', async () => {
		const { container } = render(Page);
		await waitFor(() => expect(container.textContent).not.toMatch(/checking/i));
		fireSocketEvent('game_state', {
			status: 'active',
			duration_ms: 2_700_000,
			started_at: Date.now() / 1000,
			ended_at: null,
			lobby_count: 0,
			participants: {},
		});
		flushSync();
		expect(container.querySelector('[data-testid="end-game-btn"]')).toBeTruthy();
	});
});
