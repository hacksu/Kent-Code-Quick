import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import Preview from './Preview.svelte';

beforeEach(() => {
	vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url');
	vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
});

describe('Preview.svelte', () => {
	it('renders an iframe', () => {
		const { container } = render(Preview, { html: '<p>hi</p>', css: 'p{}', js: '' });
		expect(container.querySelector('iframe')).toBeTruthy();
	});

	it('sets sandbox="allow-scripts"', () => {
		const { container } = render(Preview, { html: '', css: '', js: '' });
		const iframe = container.querySelector('iframe');
		expect(iframe?.getAttribute('sandbox')).toBe('allow-scripts');
	});

	it('renders with js prop', () => {
		const { container } = render(Preview, { html: '<b>bold</b>', css: '', js: 'console.log(1)' });
		expect(container.querySelector('iframe')).toBeTruthy();
	});

	it('renders without error when all props provided', () => {
		render(Preview, { html: '<p>test</p>', css: 'p { color: red; }', js: 'document.body.style.background="blue"' });
		expect(true).toBe(true);
	});

	it('iframe has no-referrer policy', () => {
		const { container } = render(Preview, { html: '', css: '', js: '' });
		const iframe = container.querySelector('iframe');
		expect(iframe?.getAttribute('referrerpolicy')).toBe('no-referrer');
	});
});
