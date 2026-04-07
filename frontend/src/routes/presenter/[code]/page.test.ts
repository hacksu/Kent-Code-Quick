// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import { flushSync } from 'svelte';

// ---- socket mock ----

const listeners: Record<string, ((...args: unknown[]) => void)[]> = {};
const mockSocket = {
	on: vi.fn((event: string, handler: (...args: unknown[]) => void) => {
		if (!listeners[event]) listeners[event] = [];
		listeners[event].push(handler);
	}),
	emit: vi.fn(),
	connect: vi.fn(),
};
vi.mock('socket.io-client', () => ({ io: () => mockSocket }));
vi.mock('$lib/store', () => ({ loadToken: vi.fn(() => null), saveToken: vi.fn() }));

function trigger(event: string, data: unknown) {
	(listeners[event] ?? []).forEach((h) => h(data));
}

// ---- child component mocks ----

vi.mock('$lib/components/Timer.svelte', () => ({
	default: vi.fn().mockImplementation(function () {
		return { destroy: vi.fn() };
	}),
}));
vi.mock('$lib/components/ParticipantCard.svelte', () => ({
	default: vi.fn().mockImplementation(function () {
		return { destroy: vi.fn() };
	}),
}));

// ---- $app mocks ----

const { mockPage } = vi.hoisted(() => ({
	mockPage: {
		params: { code: 'ROOM' },
		url: new URL('http://localhost/presenter/ROOM'),
	},
}));
vi.mock('$app/state', () => ({ page: mockPage }));

import Page from './+page.svelte';

beforeEach(() => {
	for (const key of Object.keys(listeners)) delete listeners[key];
	mockSocket.on.mockClear();
	mockSocket.emit.mockClear();
	mockSocket.connect.mockClear();
	mockPage.params = { code: 'ROOM' };
	mockPage.url = new URL('http://localhost/presenter/ROOM');
});

// ---- layout ----

describe('Presenter page — layout', () => {
	it('renders the presenter layout', () => {
		const { container } = render(Page);
		expect(container.querySelector('.presenter-layout')).toBeTruthy();
	});

	it('renders the header bar', () => {
		const { container } = render(Page);
		expect(container.querySelector('.header-bar')).toBeTruthy();
	});

	it('renders the participant grid', () => {
		const { container } = render(Page);
		expect(container.querySelector('.participant-grid')).toBeTruthy();
	});
});

// ---- end event button ----

describe('Presenter page — End Event button', () => {
	it('hides End Event button for presenter role', () => {
		const { container } = render(Page);
		expect(container.querySelector('.end-event-btn')).toBeNull();
	});

	it('shows End Event button for admin role', () => {
		mockPage.url = new URL('http://localhost/presenter/ROOM?role=admin');
		const { container } = render(Page);
		expect(container.querySelector('.end-event-btn')).toBeTruthy();
	});

	it('emits end_event on End Event click', async () => {
		mockPage.url = new URL('http://localhost/presenter/ROOM?role=admin');
		const { container } = render(Page);
		const btn = container.querySelector('.end-event-btn') as HTMLButtonElement;
		await fireEvent.click(btn);
		expect(mockSocket.emit).toHaveBeenCalledWith('end_event', {});
	});
});

// ---- participants ----

describe('Presenter page — participants', () => {
	it('renders no cards when participants is empty', () => {
		const { container } = render(Page);
		expect(container.querySelectorAll('.participant-item').length).toBe(0);
	});

	it('renders a card for each participant after room_state', async () => {
		const { container } = render(Page);
		trigger('room_state', {
			participants: {
				tok1: { id: 'tok1', name: 'Alice', sid: 's1', html: '', css: '', penalty_ms: 0, tab_out_count: 0, submitted_at: null, final_html: null, final_css: null, role: 'participant' },
				tok2: { id: 'tok2', name: 'Bob', sid: 's2', html: '', css: '', penalty_ms: 0, tab_out_count: 0, submitted_at: null, final_html: null, final_css: null, role: 'participant' },
			},
		});
		flushSync();
		expect(container.querySelectorAll('.participant-item').length).toBe(2);
	});
});

// ---- store initialisation ----

describe('Presenter page — store', () => {
	it('emits join with presenter role on connect', () => {
		render(Page);
		trigger('connect', undefined);
		expect(mockSocket.emit).toHaveBeenCalledWith(
			'join',
			expect.objectContaining({ room_code: 'ROOM', role: 'presenter' }),
		);
	});
});
