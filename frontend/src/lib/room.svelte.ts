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
	submitted_at: number | null;
	final_html: string | null;
	final_css: string | null;
	role: string;
}

export function createRoomStore(roomCode: string, name: string, role: string) {
	const socket: Socket = io({ autoConnect: false });

	let participants = $state<Record<string, Participant>>({});

	function emitJoin() {
		const tok = loadToken(roomCode);
		socket.emit('join', { room_code: roomCode, name, role, token: tok });
	}

	socket.on('connect', emitJoin);

	socket.on('token_assigned', ({ token: t }: { token: string }) => {
		saveToken(roomCode, t);
	});

	socket.on('room_state', (data: { participants: Record<string, Participant> }) => {
		participants = data.participants;
	});

	socket.on('participant_update', (p: Pick<Participant, 'id' | 'name' | 'html' | 'css'>) => {
		const existing = participants[p.id];
		if (existing) {
			participants[p.id] = { ...existing, ...p };
		}
	});

	socket.connect();

	return {
		socket,
		get participants() {
			return participants;
		}
	};
}
