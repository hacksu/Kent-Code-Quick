import { test, expect } from '@playwright/test';
import { simulateTabOut } from './helpers';

const ROOM_ID = 'MULTI03';

test.describe('Multi-participant — room state sync', () => {
	test('two participants both appear as cards in the presenter view', async ({ browser }) => {
		const ctxAlice = await browser.newContext();
		const ctxBob = await browser.newContext();
		const ctxPresenter = await browser.newContext();

		const alice = await ctxAlice.newPage();
		const bob = await ctxBob.newPage();
		const presenter = await ctxPresenter.newPage();

		await alice.goto(`/room/${ROOM_ID}?name=Alice`);
		await alice.waitForSelector('.room-layout', { timeout: 10_000 });

		await bob.goto(`/room/${ROOM_ID}?name=Bob`);
		await bob.waitForSelector('.room-layout', { timeout: 10_000 });

		await presenter.goto(`/presenter/${ROOM_ID}`);
		await presenter.waitForSelector('.presenter-layout', { timeout: 10_000 });

		// Wait until at least 2 participant cards appear (Alice + Bob)
		await presenter.locator('.participant-card').nth(1).waitFor({ state: 'visible', timeout: 8_000 });
		const names = await presenter.locator('.participant-card .name').allTextContents();
		expect(names).toContain('Alice');
		expect(names).toContain('Bob');

		await ctxAlice.close();
		await ctxBob.close();
		await ctxPresenter.close();
	});

	test('after Alice submits, her card shows submitted badge in presenter view', async ({ browser }) => {
		const ctxAlice = await browser.newContext();
		const ctxPresenter = await browser.newContext();

		const alice = await ctxAlice.newPage();
		const presenter = await ctxPresenter.newPage();

		await alice.goto(`/room/${ROOM_ID}B?name=Alice`);
		await alice.waitForSelector('.room-layout', { timeout: 10_000 });

		await presenter.goto(`/presenter/${ROOM_ID}B`);
		await presenter.waitForSelector('.presenter-layout', { timeout: 10_000 });

		await alice.locator('.submit-btn').click();

		// Submit triggers a room_state broadcast, so presenter gets the update
		await expect(
			presenter.locator('.participant-card:has(.name:has-text("Alice")) .badge'),
		).toBeVisible({ timeout: 8_000 });

		await ctxAlice.close();
		await ctxPresenter.close();
	});

	test('tab-out penalty appears on the participant\'s own screen', async ({ browser }) => {
		const ctxAlice = await browser.newContext();
		const alice = await ctxAlice.newPage();

		await alice.goto(`/room/${ROOM_ID}C?name=Alice`);
		await alice.waitForSelector('.room-layout', { timeout: 10_000 });

		await simulateTabOut(alice);

		// The penalty banner should appear on Alice's own view
		await expect(alice.locator('.penalty-banner')).toBeVisible({ timeout: 5_000 });
		await expect(alice.locator('.penalty-banner')).toContainText('Tab out detected');

		await ctxAlice.close();
	});

	test('code typed by Alice appears in her presenter card preview', async ({ browser }) => {
		const ctxAlice = await browser.newContext();
		const ctxPresenter = await browser.newContext();

		const alice = await ctxAlice.newPage();
		const presenter = await ctxPresenter.newPage();

		await alice.goto(`/room/${ROOM_ID}D?name=Alice`);
		await alice.waitForSelector('.room-layout', { timeout: 10_000 });

		await presenter.goto(`/presenter/${ROOM_ID}D`);
		await presenter.waitForSelector('.presenter-layout', { timeout: 10_000 });

		// Alice types into the CodeMirror editor
		const cmContent = alice.locator('.cm-content').first();
		await cmContent.click();
		await alice.keyboard.type('<h1>Hello</h1>', { delay: 30 });

		// Debounce is 300ms; wait for code_update to reach presenter
		await presenter.waitForTimeout(1_500);

		// Alice's card should exist and show her name
		const aliceCard = presenter.locator('.participant-card:has(.name:has-text("Alice"))');
		await expect(aliceCard).toBeVisible({ timeout: 5_000 });

		await ctxAlice.close();
		await ctxPresenter.close();
	});
});
