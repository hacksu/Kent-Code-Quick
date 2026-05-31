import { writable } from 'svelte/store';

export const token = writable<string | null>(null);

export function loadToken(): string | null {
	if (typeof localStorage === 'undefined') return null;
	return localStorage.getItem('eventToken');
}

export function saveToken(t: string): void {
	if (typeof localStorage === 'undefined') return;
	localStorage.setItem('eventToken', t);
	token.set(t);
}

export function clearToken(): void {
	if (typeof localStorage === 'undefined') return;
	localStorage.removeItem('eventToken');
	token.set(null);
}
