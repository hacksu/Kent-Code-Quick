import { io, type Socket } from 'socket.io-client';
import { loadToken, saveToken } from './store';

export interface Participant {
	id: string;
	name: string;
	html: string;
	css: string;
	penalty_ms: number;
	tab_out_count: number;
	copy_attempt_count: number;
	submitted_at: number | null;
	final_html: string | null;
	final_css: string | null;
}

export interface PenaltyPayload {
	penalty_ms: number;
	tab_out_count: number;
}

export interface GameStatePayload {
	status: string;
	duration_ms: number;
	started_at: number | null;
	ended_at: number | null;
	lobby_count: number;
	participants: Record<string, Participant>;
}

/** Used by /play: participant in active game. */
export function createPlayStore(token: string) {
	const socket: Socket = io({ autoConnect: false });

	let participants = $state<Record<string, Participant>>({});
	let currentPenalty = $state<PenaltyPayload | null>(null);
	let hasSubmitted = $state(false);
	let eventEnded = $state(false);
	let elapsed = $state(0);
	let durationMs = $state(45 * 60 * 1000);

	socket.on('connect', () => {
		socket.emit('join_game', { token });
	});

	socket.on('game_state', (data: GameStatePayload) => {
		participants = data.participants;
		durationMs = data.duration_ms;
		if (data.status === 'ended') eventEnded = true;
		if (data.participants[token]?.submitted_at !== null) hasSubmitted = true;
	});

	socket.on('participant_update', (p: { token: string } & Partial<Participant>) => {
		if (p.token && participants[p.token]) {
			participants[p.token] = { ...participants[p.token], ...p };
		}
	});

	socket.on('penalty', (data: PenaltyPayload) => { currentPenalty = data; });
	socket.on('submitted', () => { hasSubmitted = true; });
	socket.on('event_end', () => { eventEnded = true; });
	socket.on('timer_tick', (data: { elapsed: number }) => { elapsed = data.elapsed; });
	socket.on('game_locked', () => { window.location.href = '/'; });

	socket.connect();

	return {
		get participants() { return participants; },
		get currentPenalty() { return currentPenalty; },
		get hasSubmitted() { return hasSubmitted; },
		get eventEnded() { return eventEnded; },
		get elapsed() { return elapsed; },
		get durationMs() { return durationMs; },
		get timeRemaining() { return durationMs - elapsed; },
		get myParticipant() { return participants[token] ?? null; },
		sendCodeUpdate(html: string, css: string) { socket.emit('code_update', { html, css }); },
		sendTabOut() { socket.emit('tab_out', {}); },
		sendSubmit() { socket.emit('submit', {}); },
		sendCopyAttempt() { socket.emit('copy_attempt', {}); },
	};
}

/** Used by /admin and /watch: observer with admin session. */
export function createWatchStore() {
	const socket: Socket = io({ autoConnect: false });

	let participants = $state<Record<string, Participant>>({});
	let lobbyCount = $state(0);
	let gameStatus = $state<'waiting' | 'active' | 'ended'>('waiting');
	let elapsed = $state(0);
	let durationMs = $state(45 * 60 * 1000);
	let eventEnded = $state(false);

	socket.on('connect', () => { socket.emit('watch_game', {}); });

	socket.on('game_state', (data: GameStatePayload) => {
		participants = data.participants;
		durationMs = data.duration_ms;
		gameStatus = data.status as 'waiting' | 'active' | 'ended';
		lobbyCount = data.lobby_count;
		if (data.status === 'ended') eventEnded = true;
	});

	socket.on('lobby_update', (data: { lobby_count: number }) => { lobbyCount = data.lobby_count; });

	socket.on('participant_update', (p: { token: string } & Partial<Participant>) => {
		if (p.token && participants[p.token]) {
			participants[p.token] = { ...participants[p.token], ...p };
		}
	});

	socket.on('timer_tick', (data: { elapsed: number }) => { elapsed = data.elapsed; });

	socket.on('event_end', (data: GameStatePayload) => {
		participants = data.participants;
		eventEnded = true;
		gameStatus = 'ended';
	});

	socket.on('game_reset', () => {
		participants = {};
		lobbyCount = 0;
		gameStatus = 'waiting';
		elapsed = 0;
		eventEnded = false;
	});

	socket.connect();

	return {
		get participants() { return participants; },
		get lobbyCount() { return lobbyCount; },
		get gameStatus() { return gameStatus; },
		get elapsed() { return elapsed; },
		get durationMs() { return durationMs; },
		get eventEnded() { return eventEnded; },
		sendStartGame(durationMs: number) { socket.emit('start_game', { duration_ms: durationMs }); },
		sendEndEvent() { socket.emit('end_event', {}); },
		sendResetGame() { socket.emit('reset_game', {}); },
	};
}
