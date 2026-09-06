// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, waitFor, fireEvent } from '@testing-library/svelte';

const mockFetch = vi.fn();
global.fetch = mockFetch;

const realLocation = window.location;
let locationMock: { replace: ReturnType<typeof vi.fn>; assign: ReturnType<typeof vi.fn>; href: string; origin: string };

import Page from './+page.svelte';

beforeEach(() => {
	mockFetch.mockReset();
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

describe('Home page - auth redirect', () => {
	it('redirects an authenticated admin to /admin', async () => {
		mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ is_admin: true }) });
		render(Page);
		await waitFor(() => expect(locationMock.replace).toHaveBeenCalledWith('/admin'));
	});

	it('redirects an authenticated non-admin to /lobby', async () => {
		mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ is_admin: false }) });
		render(Page);
		await waitFor(() => expect(locationMock.replace).toHaveBeenCalledWith('/lobby'));
	});
});

describe('Home page - login', () => {
	beforeEach(() => {
		// 1) /api/auth/me -> not logged in, 2) /api/config -> OAuth client id
		mockFetch.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) });
		mockFetch.mockResolvedValueOnce({
			ok: true,
			json: async () => ({ discord_client_id: 'client-id-from-server', devdocs_url: 'http://localhost:9292' }),
		});
	});

	it('shows a Login with Discord button when not authenticated', async () => {
		const { container } = render(Page);
		await waitFor(() => expect(container.textContent).toMatch(/sign up with discord/i));
	});

	it('sends the user to Discord OAuth when login is clicked', async () => {
		const { getByRole } = render(Page);
		const btn = await waitFor(() => getByRole('button', { name: /sign up with discord/i }));
		await fireEvent.click(btn);
		expect(locationMock.href).toMatch(/^https:\/\/discord\.com\/oauth2\/authorize/);
	});

	it('uses the client id served by the backend rather than a hardcoded one', async () => {
		const { getByRole } = render(Page);
		const btn = await waitFor(() => getByRole('button', { name: /sign up with discord/i }));
		await fireEvent.click(btn);
		expect(locationMock.href).toContain('client_id=client-id-from-server');
	});

	it('sends a state parameter and remembers it for the callback to verify', async () => {
		const { getByRole } = render(Page);
		const btn = await waitFor(() => getByRole('button', { name: /sign up with discord/i }));
		await fireEvent.click(btn);
		const state = new URL(locationMock.href).searchParams.get('state');
		expect(state).toBeTruthy();
		expect(sessionStorage.getItem('oauthState')).toBe(state);
	});
});

describe('Home page - misconfigured server', () => {
	it('disables login and explains when no client id is configured', async () => {
		mockFetch.mockResolvedValueOnce({ ok: false, status: 401, json: async () => ({}) });
		mockFetch.mockResolvedValueOnce({ ok: true, json: async () => ({ discord_client_id: '' }) });
		const { getByRole, getByTestId } = render(Page);
		const btn = await waitFor(() => getByRole('button', { name: /sign up with discord/i }));
		expect((btn as HTMLButtonElement).disabled).toBe(true);
		expect(getByTestId('config-error').textContent).toMatch(/no discord client id/i);
		await fireEvent.click(btn);
		expect(locationMock.href).toBe('');
	});
});
