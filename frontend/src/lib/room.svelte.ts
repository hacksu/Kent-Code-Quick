import { io, type Socket } from 'socket.io-client';
import { loadToken, saveToken } from './store';

export interface Participant {
	id: string;
	name: string;
	sid: string;
	html: string;
	css: string;
	penalty_ms: number;
	tab_out_count: number;
	copy_attempt_count: number;
	submitted_at: number | null;
	final_html: string | null;
	final_css: string | null;
	role: string;
}

export interface PenaltyPayload {
	penalty_ms: number;
	tab_out_count: number;
}

export function createRoomStore(roomCode: string, name: string, role: string) {
	const socket: Socket = io({ autoConnect: false });

	let participants = $state<Record<string, Participant>>({});
	let currentPenalty = $state<PenaltyPayload | null>(null);
	let hasSubmitted = $state(false);
	let eventEnded = $state(false);
	let elapsed = $state(0);
	let ended = $state(false);
	let durationMs = $state(45 * 60 * 1000);
	let myToken = $state<string | null>(loadToken(roomCode));

	function emitJoin() {
		const tok = loadToken(roomCode);
		socket.emit('join', { room_code: roomCode, name, role, token: tok });
	}

	socket.on('connect', emitJoin);

	socket.on('token_assigned', ({ token: t }: { token: string }) => {
		saveToken(roomCode, t);
		myToken = t;
	});

	socket.on('room_state', (data: { participants: Record<string, Participant>; duration_ms?: number; ended_at?: number | null }) => {
		participants = data.participants;
		if (data.duration_ms !== undefined) durationMs = data.duration_ms;
		if (data.ended_at) eventEnded = true;
		const tok = myToken;
		if (tok && data.participants[tok]?.submitted_at !== null) hasSubmitted = true;
	});

	socket.on('participant_update', (p: Pick<Participant, 'id' | 'name' | 'html' | 'css'>) => {
		const existing = participants[p.id];
		if (existing) {
			participants[p.id] = { ...existing, ...p };
		}
	});

	socket.on('penalty', (data: PenaltyPayload) => {
		currentPenalty = data;
	});

	socket.on('submitted', () => {
		hasSubmitted = true;
	});

	socket.on('event_end', () => {
		eventEnded = true;
	});

	socket.on('timer_tick', (data: { elapsed: number; ended: boolean }) => {
		elapsed = data.elapsed;
		ended = data.ended;
	});

	const timeRemaining = $derived(durationMs - elapsed);
	const isOvertime = $derived(elapsed > durationMs);

	socket.connect();

	return {
		socket,
		get participants() { return participants; },
		get currentPenalty() { return currentPenalty; },
		get hasSubmitted() { return hasSubmitted; },
		get eventEnded() { return eventEnded; },
		get elapsed() { return elapsed; },
		get ended() { return ended; },
		get durationMs() { return durationMs; },
		get timeRemaining() { return timeRemaining; },
		get isOvertime() { return isOvertime; },
		get myToken() { return myToken; },
		sendCodeUpdate(html: string, css: string) {
			socket.emit('code_update', { html, css });
		},
		sendTabOut() {
			socket.emit('tab_out', {});
		},
		sendSubmit() {
			socket.emit('submit', {});
		},
		sendEndEvent() {
			socket.emit('end_event', {});
		},
		sendCopyAttempt() {
			socket.emit('copy_attempt', {});
		},
	};
}
