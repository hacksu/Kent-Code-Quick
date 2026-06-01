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
	js: '',
	submitted_at: null,
	penalty_ms: 0,
	copy_attempt_count: 0,
};

beforeEach(() => vi.clearAllMocks());

describe('ParticipantCard.svelte - rendering', () => {
	it('shows participant name', () => {
		const { getByTestId } = render(ParticipantCard, { participant: base });
		expect(getByTestId('participant-name').textContent).toBe('Alice');
	});

	it('does not show submitted badge when submitted_at is null', () => {
		const { queryByTestId } = render(ParticipantCard, { participant: base });
		expect(queryByTestId('submitted-badge')).toBeNull();
	});

	it('shows submitted badge when submitted_at is set', () => {
		const { getByTestId } = render(ParticipantCard, {
			participant: { ...base, submitted_at: 1234567890 },
		});
		expect(getByTestId('submitted-badge').textContent).toBe('submitted');
	});

	it('renders a preview wrapper', () => {
		const { getByTestId } = render(ParticipantCard, { participant: base });
		expect(getByTestId('preview-wrapper')).toBeTruthy();
	});
});

describe('ParticipantCard.svelte - reactivity', () => {
	it('renders participant name immediately', () => {
		const { getByTestId } = render(ParticipantCard, { participant: base });
		expect(getByTestId('participant-name').textContent).toBe('Alice');
	});
});
