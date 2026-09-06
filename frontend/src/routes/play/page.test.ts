// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
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

function emitCount(event: string) {
	return mockSocket.emit.mock.calls.filter(([name]) => name === event).length;
}

// The page fetches /api/config on mount for the docs panel URL.
const mockFetch = vi.fn(async () => ({
	ok: true,
	json: async () => ({ devdocs_url: 'http://localhost:9292', discord_client_id: 'cid' }),
}));
global.fetch = mockFetch as unknown as typeof fetch;

let hidden = false;
Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden });

const realLocation = window.location;
let locationMock: { href: string; replace: ReturnType<typeof vi.fn>; origin: string };

beforeEach(() => {
	mockGoto.mockClear();
	mockSocket.emit.mockClear();
	mockFetch.mockClear();
	Object.keys(listeners).forEach((k) => delete listeners[k]);
	hidden = false;
	vi.spyOn(document, 'hasFocus').mockReturnValue(true);
	locationMock = { href: '', replace: vi.fn(), origin: 'http://localhost:5001' };
	// @ts-expect-error override jsdom location for assertions
	delete window.location;
	// @ts-expect-error override jsdom location for assertions
	window.location = locationMock;
});

afterEach(() => {
	vi.restoreAllMocks();
	vi.useRealTimers();
	// @ts-expect-error restore jsdom location
	window.location = realLocation;
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


describe('Play page - tab-out penalties', () => {
	/** Leaving to another browser tab fires visibilitychange AND blur. */
	function switchAwayToAnotherTab() {
		hidden = true;
		vi.mocked(document.hasFocus).mockReturnValue(false);
		document.dispatchEvent(new Event('visibilitychange'));
		window.dispatchEvent(new Event('blur'));
		vi.advanceTimersByTime(1); // the blur handler defers a tick
	}

	function comeBack() {
		hidden = false;
		vi.mocked(document.hasFocus).mockReturnValue(true);
	}

	it('counts one penalty per departure even though two events fire', () => {
		vi.useFakeTimers();
		render(Page);
		switchAwayToAnotherTab();
		expect(emitCount('tab_out')).toBe(1);
	});

	it('still counts an alt-tab, which only fires blur', () => {
		vi.useFakeTimers();
		render(Page);
		vi.mocked(document.hasFocus).mockReturnValue(false);
		window.dispatchEvent(new Event('blur'));
		vi.advanceTimersByTime(1);
		expect(emitCount('tab_out')).toBe(1);
	});

	it('counts separate departures separately', () => {
		vi.useFakeTimers();
		render(Page);
		switchAwayToAnotherTab();
		comeBack();
		vi.advanceTimersByTime(2000);
		switchAwayToAnotherTab();
		expect(emitCount('tab_out')).toBe(2);
	});
});

describe('Play page - session handling', () => {
	it('sends the player home when the socket reports no session', () => {
		render(Page);
		fireSocketEvent('auth_required');
		expect(window.location.href).toBe('/');
	});

	it('adopts a token reissued by the server', async () => {
		const storeMock = await import('$lib/store');
		render(Page);
		fireSocketEvent('token_assigned', { token: 'recovered-token' });
		expect(vi.mocked(storeMock.saveToken)).toHaveBeenCalledWith('recovered-token');
		fireSocketEvent('connect');
		expect(mockSocket.emit).toHaveBeenCalledWith('join_game', { token: 'recovered-token' });
	});
});
