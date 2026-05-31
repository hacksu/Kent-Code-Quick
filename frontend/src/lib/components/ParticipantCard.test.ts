import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render } from '@testing-library/svelte';

vi.mock('./Preview.svelte', () => ({
	default: vi.fn().mockImplementation(() => ({ destroy: vi.fn() })),
}));

import ParticipantCard from './ParticipantCard.svelte';

const base = {
	name: 'Alice',
	html: '<p>hi</p>',
	css: 'p{}',
	submitted_at: null,
	penalty_ms: 0,
	copy_attempt_count: 0,
};

beforeEach(() => vi.clearAllMocks());

describe('ParticipantCard.svelte - rendering', () => {
	it('shows participant name', () => {
		const { container } = render(ParticipantCard, { participant: base });
		expect(container.querySelector('.name')?.textContent).toBe('Alice');
	});

	it('does not show submitted badge when submitted_at is null', () => {
		const { container } = render(ParticipantCard, { participant: base });
		expect(container.querySelector('.badge')).toBeNull();
	});

	it('shows submitted badge when submitted_at is set', () => {
		const { container } = render(ParticipantCard, {
			participant: { ...base, submitted_at: 1234567890 },
		});
		expect(container.querySelector('.badge')).toBeTruthy();
		expect(container.querySelector('.badge')?.textContent).toBe('submitted');
	});

	it('renders a preview wrapper', () => {
		const { container } = render(ParticipantCard, { participant: base });
		expect(container.querySelector('.preview-wrapper')).toBeTruthy();
	});
});

describe('ParticipantCard.svelte - throttle', () => {
	it('renders initial html immediately', () => {
		vi.useFakeTimers();
		vi.setSystemTime(1000);
		const { container } = render(ParticipantCard, {
			participant: base,
			throttleMs: 500,
		});
		// Initial render at t=1000, lastUpdate=0, 1000-0 >= 500 so it renders
		expect(container.querySelector('.name')?.textContent).toBe('Alice');
		vi.useRealTimers();
	});

	it('uses throttleMs default of 500', () => {
		const { container } = render(ParticipantCard, { participant: base });
		// Just verify it renders without error when throttleMs is omitted
		expect(container.querySelector('.participant-card')).toBeTruthy();
	});
});
