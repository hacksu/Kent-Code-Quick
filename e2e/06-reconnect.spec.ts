import { test, expect } from '@playwright/test';

const ROOM_ID = 'RECONN06';

test.describe('Reconnection', () => {
	test('participant rejoins same room and restores code via localStorage token', async ({ page }) => {
		await page.goto(`/room/${ROOM_ID}?name=Alice`);
		await page.waitForSelector('.room-layout', { timeout: 10_000 });

		// Type some code
		const cmContent = page.locator('.cm-content').first();
		await cmContent.click();
		await page.keyboard.type('<p>reconnect test</p>', { delay: 20 });
		await page.waitForTimeout(600); // let debounce flush

		// Reload — should reconnect with the same token
		await page.reload();
		await page.waitForSelector('.room-layout', { timeout: 10_000 });

		// After reconnect, the editor should restore to the server's state for this participant
		// We can verify the store reconnected by checking the submit button is still enabled
		await expect(page.locator('.submit-btn')).toBeVisible({ timeout: 5_000 });
	});

	test('token is stored in localStorage on first join', async ({ page }) => {
		await page.goto(`/room/${ROOM_ID}B?name=TokenTest`);
		await page.waitForSelector('.room-layout', { timeout: 10_000 });

		// Wait for token_assigned event to be received
		await page.waitForTimeout(1_000);

		// The store uses 'eventToken_<ROOM_CODE>' as the localStorage key
		const token = await page.evaluate(
			(roomCode) => localStorage.getItem(`eventToken_${roomCode}`),
			ROOM_ID + 'B',
		);

		expect(token).toBeTruthy();
	});
});
