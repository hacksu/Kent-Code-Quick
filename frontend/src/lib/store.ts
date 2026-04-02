import { writable } from 'svelte/store';

export const token = writable<string | null>(null);

export function loadToken(roomCode: string): string | null {
	if (typeof localStorage === 'undefined') return null;
	return localStorage.getItem(`eventToken_${roomCode}`);
}

export function saveToken(roomCode: string, t: string): void {
	localStorage.setItem(`eventToken_${roomCode}`, t);
	token.set(t);
}
