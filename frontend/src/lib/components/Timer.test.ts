import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import Timer from './Timer.svelte';

describe('Timer.svelte', () => {
	it('displays full time remaining as MM:SS', () => {
		const { getByText } = render(Timer, { elapsed: 0, durationMs: 60_000 });
		expect(getByText('1:00')).toBeTruthy();
	});

	it('counts down correctly', () => {
		const { getByText } = render(Timer, { elapsed: 30_000, durationMs: 60_000 });
		expect(getByText('0:30')).toBeTruthy();
	});

	it('displays 0:00 when exactly elapsed', () => {
		const { getByText } = render(Timer, { elapsed: 60_000, durationMs: 60_000 });
		expect(getByText('0:00')).toBeTruthy();
	});

	it('shows negative time in overtime', () => {
		const { getByText } = render(Timer, { elapsed: 65_000, durationMs: 60_000 });
		expect(getByText('-0:05')).toBeTruthy();
	});

	it('shows negative time with minutes in overtime', () => {
		const { getByText } = render(Timer, { elapsed: 125_000, durationMs: 60_000 });
		expect(getByText('-1:05')).toBeTruthy();
	});

	it('applies overtime class when elapsed exceeds durationMs', () => {
		const { container } = render(Timer, { elapsed: 65_000, durationMs: 60_000 });
		expect(container.querySelector('.overtime')).toBeTruthy();
	});

	it('does not apply overtime class when time remains', () => {
		const { container } = render(Timer, { elapsed: 30_000, durationMs: 60_000 });
		expect(container.querySelector('.overtime')).toBeNull();
	});

	it('pads seconds with leading zero', () => {
		const { getByText } = render(Timer, { elapsed: 0, durationMs: 9_000 });
		expect(getByText('0:09')).toBeTruthy();
	});

	it('turns yellow when paused', () => {
		const { container } = render(Timer, { elapsed: 30_000, durationMs: 60_000, paused: true });
		expect(container.querySelector('.paused')).toBeTruthy();
	});

	it('paused takes precedence over the overtime color', () => {
		const { container } = render(Timer, { elapsed: 65_000, durationMs: 60_000, paused: true });
		const span = container.querySelector('span')!;
		expect(span.classList.contains('paused')).toBe(true);
		expect(span.classList.contains('overtime')).toBe(false);
	});
});
