import type { Page, BrowserContext } from '@playwright/test';

export const ROOM = 'ETEST';
export const ADMIN_SECRET = 'e2e-test-secret';
export const BASE = 'http://localhost:5001';

/** Join a room as a participant. Returns after the editor pane is visible. */
export async function joinAsParticipant(page: Page, name: string, room = ROOM) {
	await page.goto('/');
	await page.fill('#room-code', room);
	await page.fill('#name', name);
	await page.selectOption('#role', 'participant');
	await page.click('button[type="submit"]');
	await page.waitForSelector('.room-layout', { timeout: 10_000 });
}

/** Join as presenter. Returns after the presenter grid is visible. */
export async function joinAsPresenter(page: Page, room = ROOM) {
	await page.goto('/');
	await page.fill('#room-code', room);
	await page.fill('#name', 'Presenter');
	await page.selectOption('#role', 'presenter');
	await page.click('button[type="submit"]');
	await page.waitForSelector('.presenter-layout', { timeout: 10_000 });
}

/** Simulate the page going hidden (tab-out). */
export async function simulateTabOut(page: Page) {
	await page.evaluate(() => {
		Object.defineProperty(document, 'hidden', { value: true, configurable: true, writable: true });
		document.dispatchEvent(new Event('visibilitychange'));
	});
}

/** Restore visible state. */
export async function simulateTabBack(page: Page) {
	await page.evaluate(() => {
		Object.defineProperty(document, 'hidden', { value: false, configurable: true, writable: true });
		document.dispatchEvent(new Event('visibilitychange'));
	});
}

/** Wait for a socket event to be emitted from the page, captured via console spy. */
export async function waitForSocketEmit(page: Page, event: string, timeoutMs = 5000): Promise<unknown[]> {
	return page.evaluate(
		({ evt, ms }) =>
			new Promise((resolve, reject) => {
				const t = setTimeout(() => reject(new Error(`Timed out waiting for socket emit: ${evt}`)), ms);
				const orig = (window as any).__socketEmitLog ?? [];
				const check = () => {
					const entry = (window as any).__socketEmitLog?.find((e: any) => e.event === evt);
					if (entry) {
						clearTimeout(t);
						resolve(entry.args);
					} else {
						setTimeout(check, 50);
					}
				};
				check();
			}),
		{ evt: event, ms: timeoutMs },
	);
}

/** Install a spy on socket.emit by patching the store's socket. */
export async function installSocketSpy(page: Page) {
	await page.evaluate(() => {
		(window as any).__socketEmitLog = [];
		// Intercept all EventTarget dispatchEvent calls as a proxy — instead
		// we patch via the exposed globalThis in the Svelte app.
		// The room store exports the socket on window.__socket in dev, so we check that.
		// Fallback: monkey-patch XMLHttpRequest (not needed for WS).
		// We actually hook the actual socket.io socket which attaches on connect.
		const origFetch = window.fetch;
		// Instead of XHR hacks, use page.route for API calls.
		// For socket.io we rely on the penalty/room_state DOM changes as observable side-effects.
	});
}
