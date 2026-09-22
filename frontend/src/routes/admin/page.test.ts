// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';
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

describe('Admin page - auth gate', () => {
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

describe('Admin page - dashboard', () => {
	beforeEach(() => {
		mockFetch.mockResolvedValue({
			ok: true,
			status: 200,
			json: async () => ({ discord_id: '1', discord_username: 'ZoeAdmin', is_admin: true }),
		});
	});

	it('shows the admin username after auth', async () => {
		const { container } = render(Page);
		await waitFor(() => expect(container.textContent).toContain('ZoeAdmin'));
	});

	it('shows a Start Game button when the game is waiting', async () => {
		const { getByRole } = render(Page);
		await waitFor(() => expect(getByRole('button', { name: /start game/i })).toBeTruthy());
	});

	it('shows the names of participants in the lobby', async () => {
		const { getByRole, getByText } = render(Page);
		await waitFor(() => expect(getByRole('button', { name: /start game/i })).toBeTruthy());
		fireSocketEvent('lobby_update', { lobby_count: 2, lobby_names: ['Alice', 'Bob'] });
		flushSync();
		expect(getByText('Alice')).toBeTruthy();
		expect(getByText('Bob')).toBeTruthy();
	});

	it('emits start_game with the chosen duration when clicked', async () => {
		const { getByRole } = render(Page);
		const btn = await waitFor(() => getByRole('button', { name: /start game/i }));
		// Start button is disabled until at least one player is in the lobby.
		fireSocketEvent('lobby_update', { lobby_count: 3 });
		flushSync();
		await fireEvent.click(btn);
		// Default duration is 100 minutes -> 6_000_000 ms.
		expect(mockSocket.emit).toHaveBeenCalledWith('start_game', {
			duration_ms: 6_000_000,
			allow_internal_clipboard: true,
		});
	});
});

describe('Admin page - landing page sign-up switch', () => {
	function adminSession(signupOpen: boolean) {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: async () => ({ discord_id: '1', discord_username: 'Admin', is_admin: true }),
		});
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: async () => ({ signup_open: signupOpen, discord_client_id: 'cid' }),
		});
	}

	it('offers to show the button while sign-ups are closed', async () => {
		adminSession(false);
		const { findByTestId } = render(Page);
		expect((await findByTestId('toggle-signup')).textContent).toMatch(/show sign-up button/i);
	});

	it('offers to hide the button once sign-ups are open', async () => {
		adminSession(true);
		const { findByTestId } = render(Page);
		expect((await findByTestId('toggle-signup')).textContent).toMatch(/hide sign-up button/i);
	});

	it('opens sign-ups and reflects what the server returns', async () => {
		adminSession(false);
		const { findByTestId } = render(Page);
		const btn = await findByTestId('toggle-signup');

		mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ signup_open: true }) });
		await fireEvent.click(btn);

		const [url, init] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
		expect(url).toBe('/api/settings');
		expect(init.method).toBe('POST');
		expect(JSON.parse(init.body)).toEqual({ signup_open: true });
		await waitFor(() => expect(btn.textContent).toMatch(/hide sign-up button/i));
	});
});

describe('Admin page - project export', () => {
	function adminSession() {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: async () => ({ discord_id: '1', discord_username: 'Admin', is_admin: true }),
		});
		mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ signup_open: false }) });
	}

	function activeGame(participants: Record<string, unknown>) {
		fireSocketEvent('game_state', {
			status: 'active',
			duration_ms: 6_000_000,
			started_at: 1,
			ended_at: null,
			allow_internal_clipboard: true,
			lobby_count: 0,
			lobby_names: [],
			participants,
		});
		flushSync();
	}

	const alice = { id: 'a', name: 'Alice', html: '', css: '', js: '', tab_out_count: 0, copy_attempt_count: 0, submitted_at: 12, final_html: null, final_css: null, final_js: null };
	const bob = { ...alice, id: 'b', name: 'Bob', submitted_at: null };

	it('stays hidden until a game has participants', async () => {
		adminSession();
		const { queryByTestId, findByRole } = render(Page);
		await findByRole('button', { name: /start game/i });
		expect(queryByTestId('export-section')).toBeNull();
	});

	it('counts how many projects are finished', async () => {
		adminSession();
		const { findByTestId } = render(Page);
		await findByTestId('toggle-signup');
		activeGame({ t1: alice, t2: bob });

		const section = await findByTestId('export-section');
		expect(section.textContent).toContain('1 of 2 projects finished');
	});

	it('cannot export finished projects while none are finished', async () => {
		adminSession();
		const { findByTestId } = render(Page);
		await findByTestId('toggle-signup');
		activeGame({ t2: bob });

		expect((await findByTestId('export-finished')).hasAttribute('disabled')).toBe(true);
		expect((await findByTestId('export-all')).hasAttribute('disabled')).toBe(false);
	});

	it('downloads a zip named by the server when exporting', async () => {
		adminSession();
		const { findByTestId } = render(Page);
		await findByTestId('toggle-signup');
		activeGame({ t1: alice, t2: bob });

		const createObjectURL = vi.fn(() => 'blob:zip');
		const revokeObjectURL = vi.fn();
		Object.assign(URL, { createObjectURL, revokeObjectURL });
		const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});

		mockFetch.mockResolvedValueOnce({
			ok: true,
			blob: async () => new Blob(['zip']),
			headers: { get: () => 'attachment; filename="kcq-projects-20250101-120000.zip"' },
		});
		await fireEvent.click(await findByTestId('export-finished'));

		expect(mockFetch).toHaveBeenLastCalledWith('/api/game/export?scope=finished');
		await waitFor(() => expect(click).toHaveBeenCalled());
		const link = click.mock.instances[0] as HTMLAnchorElement;
		expect(link.download).toBe('kcq-projects-20250101-120000.zip');
		expect(revokeObjectURL).toHaveBeenCalledWith('blob:zip');
		click.mockRestore();
	});

	it('asks for every project when exporting all', async () => {
		adminSession();
		const { findByTestId } = render(Page);
		await findByTestId('toggle-signup');
		activeGame({ t1: alice, t2: bob });

		Object.assign(URL, { createObjectURL: vi.fn(() => 'blob:zip'), revokeObjectURL: vi.fn() });
		const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
		mockFetch.mockResolvedValueOnce({
			ok: true,
			blob: async () => new Blob(['zip']),
			headers: { get: () => null },
		});

		await fireEvent.click(await findByTestId('export-all'));
		expect(mockFetch).toHaveBeenLastCalledWith('/api/game/export?scope=all');
		await waitFor(() => expect(click).toHaveBeenCalled());
		click.mockRestore();
	});

	it('surfaces the reason an export failed', async () => {
		adminSession();
		const { findByTestId } = render(Page);
		await findByTestId('toggle-signup');
		activeGame({ t1: alice });

		mockFetch.mockResolvedValueOnce({
			ok: false,
			status: 404,
			json: async () => ({ error: 'no projects to export' }),
		});
		await fireEvent.click(await findByTestId('export-finished'));

		const error = await findByTestId('export-error');
		expect(error.textContent).toContain('no projects to export');
	});
});
