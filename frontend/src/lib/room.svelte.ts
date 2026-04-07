import { io, type Socket } from 'socket.io-client';
import { loadToken, saveToken } from './store';

export function createRoomStore(roomCode: string, name: string, role: string): Socket {
	const socket: Socket = io({ autoConnect: false });

	function emitJoin() {
		const tok = loadToken(roomCode);
		socket.emit('join', { room_code: roomCode, name, role, token: tok });
	}

	socket.on('connect', emitJoin);

	socket.on('token_assigned', ({ token: t }: { token: string }) => {
		saveToken(roomCode, t);
	});

	socket.connect();

	return socket;
}
