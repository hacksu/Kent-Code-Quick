// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import userEvent from '@testing-library/user-event';

const { mockGoto } = vi.hoisted(() => ({ mockGoto: vi.fn() }));
vi.mock('$app/navigation', () => ({ goto: mockGoto }));

import Page from './+page.svelte';

beforeEach(() => mockGoto.mockClear());

describe('Landing page — validation', () => {
	it('submit button is disabled when fields are empty', () => {
		const { container } = render(Page);
		const btn = container.querySelector('button[type="submit"]') as HTMLButtonElement;
		expect(btn.disabled).toBe(true);
	});

	it('submit button is enabled when participant fields are filled', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		const inputs = container.querySelectorAll('input[type="text"]');
		await user.type(inputs[0] as HTMLElement, 'TEST');
		await user.type(inputs[1] as HTMLElement, 'Alice');
		const btn = container.querySelector('button[type="submit"]') as HTMLButtonElement;
		expect(btn.disabled).toBe(false);
	});

	it('submit button is disabled for admin when secret is empty', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		const inputs = container.querySelectorAll('input[type="text"]');
		await user.type(inputs[0] as HTMLElement, 'TEST');
		await user.type(inputs[1] as HTMLElement, 'Alice');
		await user.selectOptions(container.querySelector('select')!, 'admin');
		const btn = container.querySelector('button[type="submit"]') as HTMLButtonElement;
		expect(btn.disabled).toBe(true);
	});

	it('submit button is enabled for admin when secret is filled', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		const inputs = container.querySelectorAll('input[type="text"]');
		await user.type(inputs[0] as HTMLElement, 'TEST');
		await user.type(inputs[1] as HTMLElement, 'Alice');
		await user.selectOptions(container.querySelector('select')!, 'admin');
		await user.type(container.querySelector('input[type="password"]')!, 'hunter2');
		const btn = container.querySelector('button[type="submit"]') as HTMLButtonElement;
		expect(btn.disabled).toBe(false);
	});
});

describe('Landing page — secret field visibility', () => {
	it('does not show secret field for participant by default', () => {
		const { container } = render(Page);
		expect(container.querySelector('input[type="password"]')).toBeNull();
	});

	it('shows secret field when admin is selected', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		await user.selectOptions(container.querySelector('select')!, 'admin');
		expect(container.querySelector('input[type="password"]')).toBeTruthy();
	});

	it('hides secret field when switching back from admin', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		await user.selectOptions(container.querySelector('select')!, 'admin');
		await user.selectOptions(container.querySelector('select')!, 'participant');
		expect(container.querySelector('input[type="password"]')).toBeNull();
	});
});

describe('Landing page — navigation', () => {
	it('navigates to /room/[code]?name=... for participant', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		const inputs = container.querySelectorAll('input[type="text"]');
		await user.type(inputs[0] as HTMLElement, 'TEST');
		await user.type(inputs[1] as HTMLElement, 'Alice');
		await fireEvent.submit(container.querySelector('form')!);
		expect(mockGoto).toHaveBeenCalledWith('/room/TEST?name=Alice');
	});

	it('navigates to /presenter/[code] for presenter', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		const inputs = container.querySelectorAll('input[type="text"]');
		await user.type(inputs[0] as HTMLElement, 'TEST');
		await user.type(inputs[1] as HTMLElement, 'Alice');
		await user.selectOptions(container.querySelector('select')!, 'presenter');
		await fireEvent.submit(container.querySelector('form')!);
		expect(mockGoto).toHaveBeenCalledWith('/presenter/TEST');
	});

	it('navigates to /admin/[code]?secret=... for admin', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		const inputs = container.querySelectorAll('input[type="text"]');
		await user.type(inputs[0] as HTMLElement, 'TEST');
		await user.type(inputs[1] as HTMLElement, 'Alice');
		await user.selectOptions(container.querySelector('select')!, 'admin');
		await user.type(container.querySelector('input[type="password"]')!, 'hunter2');
		await fireEvent.submit(container.querySelector('form')!);
		expect(mockGoto).toHaveBeenCalledWith('/admin/TEST?secret=hunter2');
	});

	it('encodes special characters in name', async () => {
		const user = userEvent.setup();
		const { container } = render(Page);
		const inputs = container.querySelectorAll('input[type="text"]');
		await user.type(inputs[0] as HTMLElement, 'TEST');
		await user.type(inputs[1] as HTMLElement, 'Alice Smith');
		await fireEvent.submit(container.querySelector('form')!);
		expect(mockGoto).toHaveBeenCalledWith('/room/TEST?name=Alice%20Smith');
	});

	it('does not navigate when form is invalid', async () => {
		const { container } = render(Page);
		await fireEvent.submit(container.querySelector('form')!);
		expect(mockGoto).not.toHaveBeenCalled();
	});
});
