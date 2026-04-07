// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';

// ---- mocks ----

// Socket mock (needed because the page initialises createRoomStore)
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

// Child-component mocks
vi.mock('$lib/components/Timer.svelte', () => ({
	default: vi.fn().mockImplementation(function () {
		return { destroy: vi.fn() };
	}),
}));
vi.mock('$lib/components/Preview.svelte', () => ({
	default: vi.fn().mockImplementation(function () {
		return { destroy: vi.fn() };
	}),
}));
vi.mock('$lib/components/Editor.svelte', () => ({
	default: vi.fn().mockImplementation(function () {
		return { destroy: vi.fn() };
	}),
}));

// Controllable $app/state + $app/navigation mocks
const { mockPage, mockGoto } = vi.hoisted(() => ({
	mockPage: {
		params: { code: 'ROOM' },
		url: new URL('http://localhost/room/ROOM?name=Alice'),
	},
	mockGoto: vi.fn(),
}));
vi.mock('$app/state', () => ({ page: mockPage }));
vi.mock('$app/navigation', () => ({ goto: mockGoto }));

import Page from './+page.svelte';

beforeEach(() => {
	for (const key of Object.keys(listeners)) delete listeners[key];
	mockSocket.on.mockClear();
	mockSocket.emit.mockClear();
	mockSocket.connect.mockClear();
	mockGoto.mockClear();
	// reset to valid defaults
	mockPage.params = { code: 'ROOM' };
	mockPage.url = new URL('http://localhost/room/ROOM?name=Alice');
});

// ---- layout structure ----

describe('Room page — layout', () => {
	it('renders the room layout container', () => {
		const { container } = render(Page);
		expect(container.querySelector('.room-layout')).toBeTruthy();
	});

	it('renders the top bar', () => {
		const { container } = render(Page);
		expect(container.querySelector('.top-bar')).toBeTruthy();
	});

	it('renders the main area with two panes', () => {
		const { container } = render(Page);
		expect(container.querySelector('.main-area')).toBeTruthy();
		expect(container.querySelector('.editor-pane')).toBeTruthy();
		expect(container.querySelector('.preview-pane')).toBeTruthy();
	});

	it('renders the bottom bar', () => {
		const { container } = render(Page);
		expect(container.querySelector('.bottom-bar')).toBeTruthy();
	});

	it('renders a docs button in the bottom bar', () => {
		const { container } = render(Page);
		const docsSlot = container.querySelector('.docs-slot');
		expect(docsSlot?.querySelector('button')).toBeTruthy();
	});
});

// ---- submit button ----

describe('Room page — submit button', () => {
	it('renders the submit button enabled by default', () => {
		const { container } = render(Page);
		const btn = container.querySelector('.submit-btn') as HTMLButtonElement;
		expect(btn).toBeTruthy();
		expect(btn.disabled).toBe(false);
		expect(btn.textContent).toBe('Submit');
	});

	it('emits submit socket event on click', async () => {
		const { container } = render(Page);
		const btn = container.querySelector('.submit-btn') as HTMLButtonElement;
		await fireEvent.click(btn);
		expect(mockSocket.emit).toHaveBeenCalledWith('submit', {});
	});
});

// ---- redirect ----

describe('Room page — redirect', () => {
	it('calls goto("/") when name param is missing', () => {
		mockPage.url = new URL('http://localhost/room/ROOM');
		render(Page);
		expect(mockGoto).toHaveBeenCalledWith('/');
	});

	it('does not redirect when name param is present', () => {
		render(Page);
		expect(mockGoto).not.toHaveBeenCalled();
	});
});

// ---- store initialisation ----

describe('Room page — store', () => {
	it('emits join on socket connect with correct room code and name', () => {
		render(Page);
		// trigger connect to fire the join emit
		(listeners['connect'] ?? []).forEach((h) => h(undefined));
		expect(mockSocket.emit).toHaveBeenCalledWith(
			'join',
			expect.objectContaining({ room_code: 'ROOM', name: 'Alice' }),
		);
	});
});
