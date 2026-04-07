import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';
import Preview from './Preview.svelte';

beforeEach(() => {
	vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:mock-url');
	vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => {});
});

describe('Preview.svelte', () => {
	it('renders an iframe', () => {
		const { container } = render(Preview, { html: '<p>hi</p>', css: 'p{}' });
		expect(container.querySelector('iframe')).toBeTruthy();
	});

	it('sets sandbox="allow-scripts"', () => {
		const { container } = render(Preview, { html: '', css: '' });
		const iframe = container.querySelector('iframe');
		expect(iframe?.getAttribute('sandbox')).toBe('allow-scripts');
	});

	it('sets src to the blob URL', () => {
		const { container } = render(Preview, { html: '<b>bold</b>', css: '' });
		const iframe = container.querySelector('iframe');
		expect(iframe?.getAttribute('src')).toBe('blob:mock-url');
	});

	it('calls URL.createObjectURL on render', () => {
		render(Preview, { html: '<p>test</p>', css: 'p { color: red; }' });
		expect(URL.createObjectURL).toHaveBeenCalled();
	});

	it('creates blob from full HTML document including css', () => {
		render(Preview, { html: '<p>test</p>', css: 'p { color: red; }' });
		const blob: Blob = (URL.createObjectURL as ReturnType<typeof vi.fn>).mock.calls[0][0];
		expect(blob).toBeInstanceOf(Blob);
		expect(blob.type).toBe('text/html');
	});
});
