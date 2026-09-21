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
	disconnect: vi.fn(),
};
vi.mock('socket.io-client', () => ({ io: () => mockSocket }));
vi.mock('$lib/store', () => ({ loadToken: vi.fn(() => null), saveToken: vi.fn(), clearToken: vi.fn() }));

const mockFetch = vi.fn();
global.fetch = mockFetch;

const realLocation = window.location;
let locationMock: { replace: ReturnType<typeof vi.fn>; assign: ReturnType<typeof vi.fn>; href: string; origin: string };

function fireSocketEvent(event: string, ...args: unknown[]) {
	for (const cb of listeners[event] ?? []) cb(...args);
}

function okAuth(username = 'Alice') {
	mockFetch.mockResolvedValue({
		ok: true,
		status: 200,
		json: async () => ({
			discord_id: '1',
			discord_username: username,
			is_admin: false,
			signup_open: true,
		}),
	});
}

beforeEach(() => {
	mockFetch.mockReset();
	mockSocket.emit.mockClear();
	mockSocket.connect.mockClear();
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

describe('Lobby page', () => {
	it('renders waiting message', () => {
		okAuth();
		const { container } = render(Page);
		expect(container.textContent).toMatch(/waiting/i);
	});

	it('redirects to / when not authenticated', async () => {
		mockFetch.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) });
		render(Page);
		await waitFor(() => expect(locationMock.href).toBe('/'));
	});

	it('emits join_lobby with name on socket connect', async () => {
		okAuth('Alice');
		render(Page);
		await waitFor(() => expect(mockSocket.connect).toHaveBeenCalled());
		fireSocketEvent('connect');
		expect(mockSocket.emit).toHaveBeenCalledWith('join_lobby', expect.objectContaining({ name: 'Alice' }));
	});

	it('navigates to /play on game_start', async () => {
		okAuth();
		render(Page);
		await waitFor(() => expect(mockSocket.connect).toHaveBeenCalled());
		fireSocketEvent('game_start', { token: 'abc123' });
		flushSync();
		expect(locationMock.href).toBe('/play');
	});

	it('shows locked message on game_locked', async () => {
		okAuth();
		const { container } = render(Page);
		await waitFor(() => expect(mockSocket.connect).toHaveBeenCalled());
		fireSocketEvent('game_locked');
		flushSync();
		expect(container.textContent).toMatch(/in progress|locked/i);
	});

	it('shows lobby count from lobby_update', async () => {
		okAuth();
		const { container } = render(Page);
		await waitFor(() => expect(mockSocket.connect).toHaveBeenCalled());
		fireSocketEvent('lobby_update', { lobby_count: 5 });
		flushSync();
		expect(container.textContent).toContain('5');
	});
});

describe('Lobby page - closed sign-ups', () => {
	it('sends a player back to the landing page before sign-ups open', async () => {
		mockFetch.mockResolvedValue({
			ok: true,
			status: 200,
			json: async () => ({
				discord_id: '1',
				discord_username: 'Alice',
				is_admin: false,
				signup_open: false,
			}),
		});
		render(Page);
		await waitFor(() => expect(locationMock.href).toBe('/'));
		expect(mockSocket.connect).not.toHaveBeenCalled();
	});

	it('lets an admin through so they can test the lobby', async () => {
		mockFetch.mockResolvedValue({
			ok: true,
			status: 200,
			json: async () => ({
				discord_id: '1',
				discord_username: 'Admin',
				is_admin: true,
				signup_open: false,
			}),
		});
		render(Page);
		await waitFor(() => expect(mockSocket.connect).toHaveBeenCalled());
		expect(locationMock.href).toBe('');
	});

	it('leaves if the server closes sign-ups while waiting', async () => {
		okAuth();
		render(Page);
		await waitFor(() => expect(mockSocket.connect).toHaveBeenCalled());
		fireSocketEvent('signup_closed');
		expect(locationMock.href).toBe('/');
	});
});
