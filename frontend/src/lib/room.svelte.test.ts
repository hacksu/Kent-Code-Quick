import { describe, it, expect, vi, beforeEach } from 'vitest';

// Separate listener registry from client-to-server emit mock
const listeners: Record<string, ((...args: unknown[]) => void)[]> = {};

const mockSocket = {
	on: vi.fn((event: string, handler: (...args: unknown[]) => void) => {
		if (!listeners[event]) listeners[event] = [];
		listeners[event].push(handler);
	}),
	emit: vi.fn(),
	connect: vi.fn(),
};

/** Fire a server-to-client event on the mock socket. */
function trigger(event: string, data: unknown) {
	(listeners[event] ?? []).forEach((h) => h(data));
}

vi.mock('socket.io-client', () => ({ io: () => mockSocket }));
vi.mock('./store', () => ({ loadToken: vi.fn(() => null), saveToken: vi.fn() }));

import { createRoomStore } from './room.svelte';

beforeEach(() => {
	for (const key of Object.keys(listeners)) delete listeners[key];
	mockSocket.on.mockClear();
	mockSocket.emit.mockClear();
	mockSocket.connect.mockClear();
});

// ---- room_state ----

describe('room_state event', () => {
	it('starts with empty participants', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		expect(store.participants).toEqual({});
	});

	it('replaces participants map', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('room_state', {
			participants: {
				tok1: { id: 'tok1', name: 'Alice', sid: 's1', html: '', css: '', penalty_ms: 0, tab_out_count: 0, submitted_at: null, final_html: null, final_css: null, role: 'participant' },
			},
		});
		expect(store.participants['tok1'].name).toBe('Alice');
	});

	it('replaces the full map and removes stale entries', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('room_state', {
			participants: { tok1: { id: 'tok1', name: 'Alice', sid: 's1', html: '', css: '', penalty_ms: 0, tab_out_count: 0, submitted_at: null, final_html: null, final_css: null, role: 'participant' } },
		});
		trigger('room_state', {
			participants: { tok2: { id: 'tok2', name: 'Bob', sid: 's2', html: '', css: '', penalty_ms: 0, tab_out_count: 0, submitted_at: null, final_html: null, final_css: null, role: 'participant' } },
		});
		expect(store.participants['tok1']).toBeUndefined();
		expect(store.participants['tok2'].name).toBe('Bob');
	});
});

// ---- participant_update ----

describe('participant_update event', () => {
	it('patches only the named participant', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('room_state', {
			participants: {
				tok1: { id: 'tok1', name: 'Alice', sid: 's1', html: '', css: '', penalty_ms: 0, tab_out_count: 0, submitted_at: null, final_html: null, final_css: null, role: 'participant' },
				tok2: { id: 'tok2', name: 'Bob', sid: 's2', html: '', css: '', penalty_ms: 0, tab_out_count: 0, submitted_at: null, final_html: null, final_css: null, role: 'participant' },
			},
		});
		trigger('participant_update', { id: 'tok1', name: 'Alice', html: '<p>hi</p>', css: 'p{}' });
		expect(store.participants['tok1'].html).toBe('<p>hi</p>');
		expect(store.participants['tok2'].html).toBe('');
	});

	it('preserves unpatched fields', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('room_state', {
			participants: {
				tok1: { id: 'tok1', name: 'Alice', sid: 's1', html: '', css: '', penalty_ms: 500, tab_out_count: 2, submitted_at: null, final_html: null, final_css: null, role: 'participant' },
			},
		});
		trigger('participant_update', { id: 'tok1', name: 'Alice', html: '<b>bold</b>', css: '' });
		expect(store.participants['tok1'].penalty_ms).toBe(500);
		expect(store.participants['tok1'].tab_out_count).toBe(2);
	});

	it('ignores unknown participant id', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		expect(() => {
			trigger('participant_update', { id: 'ghost', name: 'Ghost', html: '', css: '' });
		}).not.toThrow();
		expect(store.participants['ghost']).toBeUndefined();
	});
});

// ---- token_assigned ----

describe('token_assigned event', () => {
	it('calls saveToken with the room code and token', async () => {
		const { saveToken } = await import('./store');
		createRoomStore('TEST', 'Alice', 'participant');
		trigger('token_assigned', { token: 'abc123' });
		expect(saveToken).toHaveBeenCalledWith('TEST', 'abc123');
	});
});

// ---- connect ----

describe('connect event', () => {
	it('emits join with room_code and name on connect', () => {
		createRoomStore('TEST', 'Alice', 'participant');
		trigger('connect', undefined);
		expect(mockSocket.emit).toHaveBeenCalledWith('join', expect.objectContaining({ room_code: 'TEST', name: 'Alice' }));
	});

	it('re-emits join on reconnect', () => {
		createRoomStore('TEST', 'Alice', 'participant');
		trigger('connect', undefined);
		trigger('connect', undefined);
		expect(mockSocket.emit).toHaveBeenCalledTimes(2);
	});
});
