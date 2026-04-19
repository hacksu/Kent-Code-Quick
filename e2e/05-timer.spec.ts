import { test, expect } from '@playwright/test';

const ROOM_ID = 'TIMER05';

test.describe('Timer', () => {
	test('timer slot is visible in the room view', async ({ page }) => {
		await page.goto(`/room/${ROOM_ID}?name=Alice`);
		await page.waitForSelector('.room-layout', { timeout: 10_000 });
		await expect(page.locator('.timer-slot')).toBeVisible();
	});

	test('timer is visible in the presenter view header', async ({ page }) => {
		await page.goto(`/presenter/${ROOM_ID}`);
		await page.waitForSelector('.presenter-layout', { timeout: 10_000 });
		// Timer is a <span> inside the header bar
		const headerBar = page.locator('.header-bar');
		await expect(headerBar).toBeVisible();
		await expect(headerBar.locator('span')).toBeVisible();
	});

	test('timer shows a time value once the room starts', async ({ page }) => {
		await page.goto(`/room/${ROOM_ID}?name=TimerWatch`);
		await page.waitForSelector('.room-layout', { timeout: 10_000 });
		// Wait for the first timer_tick from the server
		await page.waitForTimeout(2_000);
		const timerText = await page.locator('.timer-slot').textContent();
		expect(timerText).toMatch(/[\d-]+:\d{2}/);
	});

	test('timer advances over time', async ({ page }) => {
		await page.goto(`/room/${ROOM_ID}A?name=Watcher`);
		await page.waitForSelector('.room-layout', { timeout: 10_000 });
		await page.waitForTimeout(1_500);

		const t1 = await page.locator('.timer-slot').textContent();
		await page.waitForTimeout(3_000);
		const t2 = await page.locator('.timer-slot').textContent();

		expect(t1).toMatch(/[\d-]+:\d{2}/);
		expect(t2).toMatch(/[\d-]+:\d{2}/);
		expect(t2).not.toBe(t1);
	});
});
