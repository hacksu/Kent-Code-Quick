import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render } from '@testing-library/svelte';
import { flushSync } from 'svelte';
import PenaltyBanner from './PenaltyBanner.svelte';

beforeEach(() => {
	vi.useFakeTimers();
});

afterEach(() => {
	vi.useRealTimers();
});

describe('PenaltyBanner - visibility', () => {
	it('renders nothing when penalty is null', () => {
		const { container } = render(PenaltyBanner, { penalty: null });
		expect(container.querySelector('.penalty-banner')).toBeNull();
	});

	it('shows banner when penalty is provided', () => {
		const { container } = render(PenaltyBanner, {
			penalty: { penalty_ms: 5000, tab_out_count: 1 },
		});
		flushSync();
		expect(container.querySelector('.penalty-banner')).toBeTruthy();
	});

	it('auto-dismisses after 4 seconds', () => {
		const { container } = render(PenaltyBanner, {
			penalty: { penalty_ms: 5000, tab_out_count: 1 },
		});
		flushSync();
		expect(container.querySelector('.penalty-banner')).toBeTruthy();
		vi.advanceTimersByTime(4000);
		flushSync();
		expect(container.querySelector('.penalty-banner')).toBeNull();
	});

	it('does not dismiss before 4 seconds', () => {
		const { container } = render(PenaltyBanner, {
			penalty: { penalty_ms: 5000, tab_out_count: 1 },
		});
		flushSync();
		vi.advanceTimersByTime(3999);
		flushSync();
		expect(container.querySelector('.penalty-banner')).toBeTruthy();
	});
});

describe('PenaltyBanner - content', () => {
	it('shows the total penalty in seconds', () => {
		const { container } = render(PenaltyBanner, {
			penalty: { penalty_ms: 25000, tab_out_count: 2 },
		});
		flushSync();
		expect(container.querySelector('.penalty-banner')?.textContent).toContain('25s');
	});

	it('shows the tab-out count', () => {
		const { container } = render(PenaltyBanner, {
			penalty: { penalty_ms: 5000, tab_out_count: 1 },
		});
		flushSync();
		expect(container.querySelector('.penalty-banner')?.textContent).toContain('#1');
	});

	it('shows next penalty step', () => {
		const { container } = render(PenaltyBanner, {
			penalty: { penalty_ms: 5000, tab_out_count: 1 },
		});
		flushSync();
		// After 1 tab-out, next step is index 1 = 25s
		expect(container.querySelector('.penalty-banner')?.textContent).toContain('next: 25s');
	});

	it('caps next penalty at last step', () => {
		const { container } = render(PenaltyBanner, {
			penalty: { penalty_ms: 5000, tab_out_count: 999 },
		});
		flushSync();
		expect(container.querySelector('.penalty-banner')?.textContent).toContain('next: 960s');
	});
});

describe('PenaltyBanner - timer reset', () => {
	it('resets the dismiss timer when a new penalty arrives', async () => {
		const { container, rerender } = render(PenaltyBanner, {
			penalty: { penalty_ms: 5000, tab_out_count: 1 },
		});
		flushSync();
		vi.advanceTimersByTime(3000);
		flushSync();
		// new penalty at t=3000
		await rerender({ penalty: { penalty_ms: 30000, tab_out_count: 2 } });
		flushSync();
		vi.advanceTimersByTime(3000);
		flushSync();
		// 3000ms after new penalty - should still be visible
		expect(container.querySelector('.penalty-banner')).toBeTruthy();
	});
});
