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
	disconnect: vi.fn(),
};
vi.mock('socket.io-client', () => ({ io: () => mockSocket }));
vi.mock('$lib/store', () => ({ loadToken: vi.fn(() => null), saveToken: vi.fn(), clearToken: vi.fn() }));

function fireSocketEvent(event: string, ...args: unknown[]) {
	for (const cb of listeners[event] ?? []) cb(...args);
}

beforeEach(() => {
	mockGoto.mockClear();
	mockSocket.emit.mockClear();
	mockSocket.connect.mockClear();
	Object.keys(listeners).forEach((k) => delete listeners[k]);
	sessionStorage.setItem('name', 'Alice');
});

import Page from './+page.svelte';

describe('Lobby page', () => {
	it('renders waiting message', () => {
		const { container } = render(Page);
		expect(container.textContent).toMatch(/waiting/i);
	});

	it('redirects to / when no name in sessionStorage', () => {
		sessionStorage.clear();
		render(Page);
		expect(mockGoto).toHaveBeenCalledWith('/');
	});

	it('emits join_lobby with name on socket connect', () => {
		render(Page);
		fireSocketEvent('connect');
		expect(mockSocket.emit).toHaveBeenCalledWith('join_lobby', expect.objectContaining({ name: 'Alice' }));
	});

	it('navigates to /play on game_start and saves token', () => {
		render(Page);
		fireSocketEvent('game_start', { token: 'abc123' });
		flushSync();
		expect(mockGoto).toHaveBeenCalledWith('/play');
	});

	it('shows locked message on game_locked', () => {
		const { container } = render(Page);
		fireSocketEvent('game_locked');
		flushSync();
		expect(container.textContent).toMatch(/in progress|locked/i);
	});

	it('shows lobby count from lobby_update', () => {
		const { container } = render(Page);
		fireSocketEvent('lobby_update', { lobby_count: 5 });
		flushSync();
		expect(container.textContent).toContain('5');
	});
});
