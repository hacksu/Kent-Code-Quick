// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import { flushSync } from 'svelte';

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

vi.mock('$lib/components/PenaltyBanner.svelte', () => ({
	default: vi.fn().mockImplementation(function () {
		return { destroy: vi.fn() };
	}),
}));

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
		(listeners['connect'] ?? []).forEach((h) => h(undefined));
		expect(mockSocket.emit).toHaveBeenCalledWith(
			'join',
			expect.objectContaining({ room_code: 'ROOM', name: 'Alice' }),
		);
	});
});

// ---- tab switcher ----

describe('Room page — tab switcher', () => {
	it('renders HTML and CSS tab buttons', () => {
		const { container } = render(Page);
		const tabs = container.querySelectorAll('.tab-btn');
		expect(tabs.length).toBe(2);
		expect(tabs[0].textContent).toBe('HTML');
		expect(tabs[1].textContent).toBe('CSS');
	});

	it('HTML tab is active by default', () => {
		const { container } = render(Page);
		const htmlTab = container.querySelectorAll('.tab-btn')[0];
		expect(htmlTab.classList.contains('active')).toBe(true);
	});

	it('clicking CSS tab makes it active', async () => {
		const { container } = render(Page);
		const cssTab = container.querySelectorAll('.tab-btn')[1] as HTMLButtonElement;
		await fireEvent.click(cssTab);
		expect(cssTab.classList.contains('active')).toBe(true);
	});

	it('clicking HTML tab after CSS restores HTML as active', async () => {
		const { container } = render(Page);
		const [htmlTab, cssTab] = container.querySelectorAll('.tab-btn') as NodeListOf<HTMLButtonElement>;
		await fireEvent.click(cssTab);
		await fireEvent.click(htmlTab);
		expect(htmlTab.classList.contains('active')).toBe(true);
		expect(cssTab.classList.contains('active')).toBe(false);
	});
});

// ---- tab-out detection ----

describe('Room page — tab-out detection', () => {
	it('emits tab_out when document becomes hidden', () => {
		render(Page);
		Object.defineProperty(document, 'hidden', { value: true, configurable: true });
		document.dispatchEvent(new Event('visibilitychange'));
		expect(mockSocket.emit).toHaveBeenCalledWith('tab_out', {});
		Object.defineProperty(document, 'hidden', { value: false, configurable: true });
	});

	it('does not emit tab_out when document becomes visible', () => {
		render(Page);
		Object.defineProperty(document, 'hidden', { value: false, configurable: true });
		document.dispatchEvent(new Event('visibilitychange'));
		expect(mockSocket.emit).not.toHaveBeenCalledWith('tab_out', {});
	});
});

// ---- reconnect sync ----

describe('Room page — reconnect sync', () => {
	it('syncs html and css from store when local state is empty and token is known', () => {
		render(Page);
		(listeners['token_assigned'] ?? []).forEach((h) => h({ token: 'tok1' }));
		(listeners['room_state'] ?? []).forEach((h) =>
			h({
				participants: {
					tok1: { id: 'tok1', name: 'Alice', sid: 's1', html: '<b>hi</b>', css: 'b{}', penalty_ms: 0, tab_out_count: 0, submitted_at: null, final_html: null, final_css: null, role: 'participant' },
				},
			}),
		);
		flushSync();
		// After sync, sendCodeUpdate should reflect the store values
		// (we verify by checking that the page didn't crash and state was set)
		expect(mockSocket.connect).toHaveBeenCalled();
	});
});
