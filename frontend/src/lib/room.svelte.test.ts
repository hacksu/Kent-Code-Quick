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

	it('starts with null myToken', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		expect(store.myToken).toBeNull();
	});

	it('sets myToken on token_assigned', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('token_assigned', { token: 'abc123' });
		expect(store.myToken).toBe('abc123');
	});
});

// ---- penalty ----

describe('penalty event', () => {
	it('starts with null currentPenalty', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		expect(store.currentPenalty).toBeNull();
	});

	it('updates currentPenalty on penalty event', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('penalty', { penalty_ms: 5000, tab_out_count: 1 });
		expect(store.currentPenalty).toEqual({ penalty_ms: 5000, tab_out_count: 1 });
	});

	it('replaces currentPenalty on subsequent penalty events', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('penalty', { penalty_ms: 5000, tab_out_count: 1 });
		trigger('penalty', { penalty_ms: 30000, tab_out_count: 2 });
		expect(store.currentPenalty?.tab_out_count).toBe(2);
	});
});

// ---- submitted ----

describe('submitted event', () => {
	it('starts with hasSubmitted false', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		expect(store.hasSubmitted).toBe(false);
	});

	it('sets hasSubmitted true on submitted event', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('submitted', undefined);
		expect(store.hasSubmitted).toBe(true);
	});
});

// ---- event_end ----

describe('event_end event', () => {
	it('starts with eventEnded false', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		expect(store.eventEnded).toBe(false);
	});

	it('sets eventEnded true on event_end event', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('event_end', undefined);
		expect(store.eventEnded).toBe(true);
	});
});

// ---- actions ----

describe('store actions', () => {
	it('sendCodeUpdate emits code_update', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		store.sendCodeUpdate('<p>hi</p>', 'p{}');
		expect(mockSocket.emit).toHaveBeenCalledWith('code_update', { html: '<p>hi</p>', css: 'p{}' });
	});

	it('sendTabOut emits tab_out', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		store.sendTabOut();
		expect(mockSocket.emit).toHaveBeenCalledWith('tab_out', {});
	});

	it('sendSubmit emits submit', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		store.sendSubmit();
		expect(mockSocket.emit).toHaveBeenCalledWith('submit', {});
	});

	it('sendEndEvent emits end_event', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		store.sendEndEvent();
		expect(mockSocket.emit).toHaveBeenCalledWith('end_event', {});
	});
});

// ---- timer_tick ----

describe('timer_tick event', () => {
	it('starts with elapsed 0', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		expect(store.elapsed).toBe(0);
	});

	it('starts with ended false', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		expect(store.ended).toBe(false);
	});

	it('updates elapsed on timer_tick', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('timer_tick', { elapsed: 10000, ended: false });
		expect(store.elapsed).toBe(10000);
	});

	it('updates ended on timer_tick', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('timer_tick', { elapsed: 2700000, ended: true });
		expect(store.ended).toBe(true);
	});

	it('timeRemaining is durationMs - elapsed', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('timer_tick', { elapsed: 60000, ended: false });
		expect(store.timeRemaining).toBe(store.durationMs - 60000);
	});

	it('isOvertime is false when elapsed < durationMs', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('timer_tick', { elapsed: 1000, ended: false });
		expect(store.isOvertime).toBe(false);
	});

	it('isOvertime is true when elapsed > durationMs', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('timer_tick', { elapsed: store.durationMs + 1000, ended: true });
		expect(store.isOvertime).toBe(true);
	});

	it('updates durationMs from room_state', () => {
		const store = createRoomStore('TEST', 'Alice', 'participant');
		trigger('room_state', { participants: {}, duration_ms: 30 * 60 * 1000 });
		expect(store.durationMs).toBe(30 * 60 * 1000);
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
