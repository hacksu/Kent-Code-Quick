// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, fireEvent, waitFor } from '@testing-library/svelte';

vi.mock('$lib/components/ParticleBackground.svelte', () => ({
	default: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
}));

const mockFetch = vi.fn();
global.fetch = mockFetch;

const realLocation = window.location;
let locationMock: { replace: ReturnType<typeof vi.fn>; href: string; origin: string };

beforeEach(() => {
	mockFetch.mockReset();
	sessionStorage.clear();
	locationMock = { replace: vi.fn(), href: '', origin: 'http://localhost:5001' };
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

/** Not signed in, and the server reports the given client id. */
function anonymousWithClientId(clientId: string) {
	mockFetch.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) });
	mockFetch.mockResolvedValueOnce({
		ok: true,
		json: async () => ({ discord_client_id: clientId, signup_open: false }),
	});
}

describe('/login', () => {
	it('offers Discord sign-in even while sign-ups are closed', async () => {
		anonymousWithClientId('cid-123');
		const { findByTestId } = render(Page);
		const btn = await findByTestId('discord-login');
		expect(btn.hasAttribute('disabled')).toBe(false);
	});

	it('sends the browser to Discord with a stored CSRF state', async () => {
		anonymousWithClientId('cid-123');
		const { findByTestId } = render(Page);
		await fireEvent.click(await findByTestId('discord-login'));

		const state = sessionStorage.getItem('oauthState');
		expect(state).toBeTruthy();

		const target = new URL(locationMock.href);
		expect(target.origin + target.pathname).toBe('https://discord.com/oauth2/authorize');
		expect(target.searchParams.get('client_id')).toBe('cid-123');
		expect(target.searchParams.get('state')).toBe(state);
		expect(target.searchParams.get('redirect_uri')).toBe('http://localhost:5001/auth/callback');
		expect(target.searchParams.get('scope')).toBe('identify guilds.members.read');
	});

	it('sends an already signed-in admin straight to /admin', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: async () => ({ discord_id: '1', discord_username: 'Admin', is_admin: true }),
		});
		render(Page);
		await waitFor(() => expect(locationMock.replace).toHaveBeenCalledWith('/admin'));
	});

	it('sends an already signed-in player to /lobby once sign-ups are open', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: async () => ({
				discord_id: '2',
				discord_username: 'Player',
				is_admin: false,
				signup_open: true,
			}),
		});
		render(Page);
		await waitFor(() => expect(locationMock.replace).toHaveBeenCalledWith('/lobby'));
	});

	it('sends a signed-in player back to the landing page before sign-ups open', async () => {
		mockFetch.mockResolvedValueOnce({
			ok: true,
			status: 200,
			json: async () => ({
				discord_id: '2',
				discord_username: 'Player',
				is_admin: false,
				signup_open: false,
			}),
		});
		render(Page);
		await waitFor(() => expect(locationMock.replace).toHaveBeenCalledWith('/'));
	});

	it('explains itself when the server has no Discord client id', async () => {
		anonymousWithClientId('');
		const { findByTestId } = render(Page);
		expect((await findByTestId('discord-login')).hasAttribute('disabled')).toBe(true);
		expect((await findByTestId('config-error')).textContent).toMatch(/no discord client id/i);
	});
});
