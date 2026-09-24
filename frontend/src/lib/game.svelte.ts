import { io, type Socket } from 'socket.io-client';
import { saveToken } from './store';

export const DEFAULT_DURATION_MS = 100 * 60 * 1000;

export interface Participant {
	id: string;
	name: string;
	html: string;
	css: string;
	js: string;
	tab_out_count: number;
	copy_attempt_count: number;
	submitted_at: number | null;
	final_html: string | null;
	final_css: string | null;
	final_js: string | null;
}

export interface PenaltyPayload {
	type: 'tab_out' | 'copy';
	count: number;
}

export interface GameStatePayload {
	status: string;
	duration_ms: number;
	started_at: number | null;
	ended_at: number | null;
	allow_internal_clipboard: boolean;
	paused: boolean;
	lobby_count: number;
	lobby_names: string[];
	participants: Record<string, Participant>;
}

/** Used by /play: participant in active game. */
export function createPlayStore(token: string) {
	const socket: Socket = io({ autoConnect: false });

	let activeToken = $state(token);
	let participants = $state<Record<string, Participant>>({});
	let currentPenalty = $state<PenaltyPayload | null>(null);
	let eventEnded = $state(false);
	let elapsed = $state(0);
	let durationMs = $state(DEFAULT_DURATION_MS);
	let allowInternalClipboard = $state(true);
	let paused = $state(false);

	socket.on('connect', () => {
		socket.emit('join_game', { token: activeToken });
	});

	socket.on('token_assigned', ({ token: reissued }: { token: string }) => {
		activeToken = reissued;
		saveToken(reissued);
	});

	socket.on('game_state', (data: GameStatePayload) => {
		participants = data.participants;
		durationMs = data.duration_ms;
		allowInternalClipboard = data.allow_internal_clipboard;
		paused = data.paused;
		if (data.status === 'ended') eventEnded = true;
	});

	socket.on('participant_update', (p: { token: string } & Partial<Participant>) => {
		if (p.token && participants[p.token]) {
			participants[p.token] = { ...participants[p.token], ...p };
		}
	});

	socket.on('penalty', (data: PenaltyPayload) => { currentPenalty = data; });
	socket.on('event_end', () => { eventEnded = true; });
	socket.on('timer_tick', (data: { elapsed: number }) => { elapsed = data.elapsed; });
	socket.on('game_paused', (data: { paused: boolean }) => { paused = data.paused; });
	socket.on('game_locked', () => { window.location.href = '/'; });
	socket.on('auth_required', () => { window.location.href = '/'; });

	socket.connect();

	return {
		get participants() { return participants; },
		get currentPenalty() { return currentPenalty; },
		get eventEnded() { return eventEnded; },
		get elapsed() { return elapsed; },
		get durationMs() { return durationMs; },
		get allowInternalClipboard() { return allowInternalClipboard; },
		get paused() { return paused; },
		get timeRemaining() { return durationMs - elapsed; },
		get myParticipant() { return participants[activeToken] ?? null; },
		sendCodeUpdate(html: string, css: string, js: string) { socket.emit('code_update', { html, css, js }); },
		sendTabOut() { socket.emit('tab_out', {}); },
		sendCopyAttempt() { socket.emit('copy_attempt', {}); },
	};
}

/** Used by /admin and /watch: observer with admin session. */
export function createWatchStore() {
	const socket: Socket = io({ autoConnect: false });

	let participants = $state<Record<string, Participant>>({});
	let lobbyCount = $state(0);
	let lobbyNames = $state<string[]>([]);
	let gameStatus = $state<'waiting' | 'active' | 'ended'>('waiting');
	let elapsed = $state(0);
	let durationMs = $state(DEFAULT_DURATION_MS);
	let allowInternalClipboard = $state(true);
	let paused = $state(false);
	let eventEnded = $state(false);

	socket.on('connect', () => { socket.emit('watch_game', {}); });

	socket.on('game_state', (data: GameStatePayload) => {
		participants = data.participants;
		durationMs = data.duration_ms;
		allowInternalClipboard = data.allow_internal_clipboard;
		paused = data.paused;
		gameStatus = data.status as 'waiting' | 'active' | 'ended';
		lobbyCount = data.lobby_count;
		lobbyNames = data.lobby_names ?? [];
		if (data.status === 'ended') eventEnded = true;
	});

	socket.on('lobby_update', (data: { lobby_count: number; lobby_names?: string[] }) => {
		lobbyCount = data.lobby_count;
		lobbyNames = data.lobby_names ?? [];
	});

	socket.on('participant_update', (p: { token: string } & Partial<Participant>) => {
		if (p.token && participants[p.token]) {
			participants[p.token] = { ...participants[p.token], ...p };
		}
	});

	socket.on('timer_tick', (data: { elapsed: number }) => { elapsed = data.elapsed; });
	socket.on('game_paused', (data: { paused: boolean }) => { paused = data.paused; });
	socket.on('auth_required', () => { window.location.href = '/'; });

	socket.on('event_end', (data: GameStatePayload) => {
		participants = data.participants;
		eventEnded = true;
		gameStatus = 'ended';
	});

	socket.on('game_reset', () => {
		participants = {};
		lobbyCount = 0;
		lobbyNames = [];
		gameStatus = 'waiting';
		elapsed = 0;
		eventEnded = false;
		allowInternalClipboard = true;
		paused = false;
	});

	socket.connect();

	return {
		get participants() { return participants; },
		get lobbyCount() { return lobbyCount; },
		get lobbyNames() { return lobbyNames; },
		get gameStatus() { return gameStatus; },
		get elapsed() { return elapsed; },
		get durationMs() { return durationMs; },
		get allowInternalClipboard() { return allowInternalClipboard; },
		get paused() { return paused; },
		get eventEnded() { return eventEnded; },
		sendStartGame(durationMs: number, allowInternalClipboard: boolean) {
			socket.emit('start_game', { duration_ms: durationMs, allow_internal_clipboard: allowInternalClipboard });
		},
		sendEndEvent() { socket.emit('end_event', {}); },
		sendResetGame() { socket.emit('reset_game', {}); },
		sendPauseGame() { socket.emit('pause_game', {}); },
		sendResumeGame() { socket.emit('resume_game', {}); },
	};
}
