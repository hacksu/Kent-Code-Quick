import { test, expect } from '@playwright/test';

const ROOM_ID = 'ADMIN04';
const SECRET = 'e2e-test-secret';

test.describe('Admin view', () => {
	test('shows "Invalid secret" with wrong secret', async ({ page }) => {
		await page.goto(`/admin/${ROOM_ID}?secret=wrong`);
		await expect(page.locator('text=Invalid secret')).toBeVisible({ timeout: 5_000 });
	});

	test('shows "Room not found" for nonexistent room with valid secret', async ({ page }) => {
		await page.goto(`/admin/DOESNOTEXIST?secret=${SECRET}`);
		await expect(page.locator('text=not found')).toBeVisible({ timeout: 5_000 });
	});

	test('shows participant in sidebar and submitted badge in detail after submit', async ({ browser }) => {
		const ctxAlice = await browser.newContext();
		const alice = await ctxAlice.newPage();

		await alice.goto(`/room/${ROOM_ID}C?name=Alice`);
		await alice.waitForSelector('.room-layout', { timeout: 10_000 });

		// Type some code so final_html is non-empty
		const cmContent = alice.locator('.cm-content').first();
		await cmContent.click();
		await alice.keyboard.type('<b>hello</b>', { delay: 30 });
		await alice.waitForTimeout(500); // let debounce flush to server

		await alice.locator('.submit-btn').click();
		await expect(alice.locator('.submit-slot')).toContainText('Submitted', { timeout: 5_000 });

		// Admin view
		const adminPage = await browser.newPage();
		await adminPage.goto(`/admin/${ROOM_ID}C?secret=${SECRET}`);

		// Alice should appear in the sidebar
		await expect(adminPage.locator('aside button', { hasText: 'Alice' })).toBeVisible({ timeout: 8_000 });

		// Click Alice to view her submission
		await adminPage.locator('aside button', { hasText: 'Alice' }).click();

		// The detail header should show the submitted badge
		await expect(adminPage.locator('span', { hasText: 'submitted' })).toBeVisible({ timeout: 5_000 });

		await ctxAlice.close();
		await adminPage.close();
	});

	test('clicking a participant shows their final code with HTML/CSS tabs', async ({ browser }) => {
		const ctxBob = await browser.newContext();
		const bob = await ctxBob.newPage();

		await bob.goto(`/room/${ROOM_ID}D?name=Bob`);
		await bob.waitForSelector('.room-layout', { timeout: 10_000 });

		// Type code — enough delay so the debounce fires and code_update reaches the server
		const cmContent = bob.locator('.cm-content').first();
		await cmContent.click();
		await bob.keyboard.type('<p>Bob was here</p>', { delay: 30 });
		await bob.waitForTimeout(600); // debounce is 300ms, give extra headroom

		await bob.locator('.submit-btn').click();
		await expect(bob.locator('.submit-slot')).toContainText('Submitted', { timeout: 5_000 });

		const adminPage = await browser.newPage();
		await adminPage.goto(`/admin/${ROOM_ID}D?secret=${SECRET}`);

		// Bob is selected automatically (first participant)
		await expect(adminPage.locator('aside button', { hasText: 'Bob' })).toBeVisible({ timeout: 8_000 });

		// The HTML/CSS tab buttons should be visible in the detail section
		// (They appear when final_html or final_css is non-empty)
		const detailSection = adminPage.locator('.flex.flex-1.flex-col');
		await expect(detailSection.locator('button', { hasText: 'HTML' })).toBeVisible({ timeout: 5_000 });
		await expect(detailSection.locator('button', { hasText: 'CSS' })).toBeVisible({ timeout: 5_000 });

		await ctxBob.close();
		await adminPage.close();
	});
});
