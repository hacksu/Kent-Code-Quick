// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';

const { mockGoto } = vi.hoisted(() => ({ mockGoto: vi.fn() }));
vi.mock('$app/navigation', () => ({ goto: mockGoto }));

import Page from './+page.svelte';

beforeEach(() => {
	mockGoto.mockClear();
	sessionStorage.clear();
});

describe('Home page - validation', () => {
	it('submit button is disabled when name is empty', () => {
		const { container } = render(Page);
		const btn = container.querySelector('button[type="submit"]') as HTMLButtonElement;
		expect(btn.disabled).toBe(true);
	});

	it('submit button is enabled when name is filled', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		await user.type(container.querySelector('input')!, 'Alice');
		const btn = container.querySelector('button[type="submit"]') as HTMLButtonElement;
		expect(btn.disabled).toBe(false);
	});
});

describe('Home page - navigation', () => {
	it('saves name to sessionStorage and navigates to /lobby', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		await user.type(container.querySelector('input')!, 'Alice');
		await fireEvent.submit(container.querySelector('form')!);
		expect(sessionStorage.getItem('name')).toBe('Alice');
		expect(mockGoto).toHaveBeenCalledWith('/lobby');
	});

	it('trims whitespace from name before saving', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		await user.type(container.querySelector('input')!, '  Bob  ');
		await fireEvent.submit(container.querySelector('form')!);
		expect(sessionStorage.getItem('name')).toBe('Bob');
	});

	it('does not navigate when form is invalid', async () => {
		const { container } = render(Page);
		await fireEvent.submit(container.querySelector('form')!);
		expect(mockGoto).not.toHaveBeenCalled();
	});
});

describe('Home page - admin link', () => {
	it('has an admin login link pointing to Discord OAuth', () => {
		const { container } = render(Page);
		const link = container.querySelector('a[href="/auth/discord?next=/admin"]') as HTMLAnchorElement;
		expect(link).toBeTruthy();
		expect(link.textContent).toMatch(/admin/i);
	});
});
