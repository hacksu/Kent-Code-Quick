import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';

// Mock the child card so the test doesn't mount a real preview iframe.
vi.mock('./ParticipantCard.svelte', () => ({
	default: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
}));

import ParticipantFocus from './ParticipantFocus.svelte';

const participant = {
	name: 'Alice',
	html: '<p>hi</p>',
	css: 'p{}',
	js: '',
	submitted_at: null,
	tab_out_count: 0,
	copy_attempt_count: 0,
};

function noop() {}

beforeEach(() => vi.clearAllMocks());

describe('ParticipantFocus.svelte', () => {
	it('shows the focused participant name', () => {
		const { getByTestId } = render(ParticipantFocus, {
			participant,
			index: 0,
			total: 3,
			onPrev: noop,
			onNext: noop,
			onClose: noop,
		});
		expect(getByTestId('focus-name').textContent).toBe('Alice');
	});

	it('shows a 1-based position out of total', () => {
		const { getByTestId } = render(ParticipantFocus, {
			participant,
			index: 2,
			total: 5,
			onPrev: noop,
			onNext: noop,
			onClose: noop,
		});
		expect(getByTestId('focus-position').textContent).toBe('3 / 5');
	});

	it('invokes navigation callbacks on button clicks', () => {
		const onPrev = vi.fn();
		const onNext = vi.fn();
		const onClose = vi.fn();
		const { getByTestId } = render(ParticipantFocus, {
			participant,
			index: 1,
			total: 3,
			onPrev,
			onNext,
			onClose,
		});

		getByTestId('focus-prev').click();
		getByTestId('focus-next').click();
		getByTestId('focus-close').click();

		expect(onPrev).toHaveBeenCalledTimes(1);
		expect(onNext).toHaveBeenCalledTimes(1);
		expect(onClose).toHaveBeenCalledTimes(1);
	});

	it('disables prev/next when there is only one participant', () => {
		const { getByTestId } = render(ParticipantFocus, {
			participant,
			index: 0,
			total: 1,
			onPrev: noop,
			onNext: noop,
			onClose: noop,
		});
		expect((getByTestId('focus-prev') as HTMLButtonElement).disabled).toBe(true);
		expect((getByTestId('focus-next') as HTMLButtonElement).disabled).toBe(true);
	});
});
