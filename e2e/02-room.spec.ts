import { test, expect, type Page } from '@playwright/test';
import { ROOM, ADMIN_SECRET, joinAsParticipant, simulateTabOut, simulateTabBack } from './helpers';

const ROOM_ID = 'ROOM02';

async function joinRoom(page: Page, name: string) {
	await page.goto(`/room/${ROOM_ID}?name=${encodeURIComponent(name)}`);
	await page.waitForSelector('.room-layout', { timeout: 10_000 });
}

test.describe('Participant room — layout', () => {
	test('renders editor layout with tabs, preview, timer, submit', async ({ page }) => {
		await joinRoom(page, 'Alice');
		await expect(page.locator('.editor-pane')).toBeVisible();
		await expect(page.locator('.preview-pane')).toBeVisible();
		await expect(page.locator('.top-bar')).toBeVisible();
		await expect(page.locator('.bottom-bar')).toBeVisible();
		await expect(page.locator('.submit-btn')).toBeVisible();
	});

	test('HTML and CSS tabs are present and HTML is active by default', async ({ page }) => {
		await joinRoom(page, 'Alice');
		const tabs = page.locator('.tab-btn');
		await expect(tabs.nth(0)).toHaveText('HTML');
		await expect(tabs.nth(1)).toHaveText('CSS');
		await expect(tabs.nth(0)).toHaveClass(/active/);
	});

	test('clicking CSS tab makes CSS active', async ({ page }) => {
		await joinRoom(page, 'Alice');
		await page.locator('.tab-btn').nth(1).click();
		await expect(page.locator('.tab-btn').nth(1)).toHaveClass(/active/);
		await expect(page.locator('.tab-btn').nth(0)).not.toHaveClass(/active/);
	});

	test('docs button toggles the docs panel', async ({ page }) => {
		await joinRoom(page, 'Alice');
		const docsPanel = page.locator('.docs-panel');
		// Panel starts hidden (display:none via Tailwind `hidden` class)
		await expect(docsPanel).toBeHidden();
		await page.locator('.docs-slot button').click();
		await expect(docsPanel).toBeVisible();
		await page.locator('.docs-slot button').click();
		await expect(docsPanel).toBeHidden();
	});

	test('redirects to / if name param is missing', async ({ page }) => {
		await page.goto(`/room/${ROOM_ID}`);
		await expect(page).toHaveURL('/');
	});
});

test.describe('Participant room — submit', () => {
	test('submit button is enabled before submitting', async ({ page }) => {
		await joinRoom(page, 'Alice');
		await expect(page.locator('.submit-btn')).toBeEnabled();
	});

	test('after submit, button is replaced with "Submitted" badge', async ({ page }) => {
		await joinRoom(page, 'Submitter');
		await page.locator('.submit-btn').click();
		// Server will emit "submitted" which makes store.hasSubmitted = true
		await expect(page.locator('.submit-slot')).toContainText('Submitted', { timeout: 5_000 });
		await expect(page.locator('.submit-btn')).toHaveCount(0);
	});

	test('after submit, editor content is not editable (CodeMirror readOnly)', async ({ page }) => {
		await joinRoom(page, 'Submitter2');
		await page.locator('.submit-btn').click();
		await expect(page.locator('.submit-slot')).toContainText('Submitted', { timeout: 5_000 });
		// CodeMirror sets aria-readonly="true" on .cm-content when EditorState.readOnly is active
		const cmContent = page.locator('.cm-content').first();
		await expect(cmContent).toHaveAttribute('aria-readonly', 'true', { timeout: 5_000 });
	});
});

test.describe('Participant room — tab-out penalty', () => {
	test('simulated tab-out shows a penalty banner', async ({ page }) => {
		await joinRoom(page, 'TabTester');
		// no penalty before
		await expect(page.locator('.penalty-banner')).toHaveCount(0);

		await simulateTabOut(page);

		// Server broadcasts a penalty event; PenaltyBanner should appear
		await expect(page.locator('.penalty-banner')).toBeVisible({ timeout: 5_000 });
	});

	test('escalating tab-outs increase penalty', async ({ page }) => {
		await joinRoom(page, 'Escalator');

		// First tab-out: 5s penalty
		await simulateTabOut(page);
		await simulateTabBack(page);
		await expect(page.locator('.penalty-banner')).toBeVisible({ timeout: 5_000 });
		const first = await page.locator('.penalty-banner').textContent();

		// Second tab-out: 25s penalty
		await simulateTabOut(page);
		await simulateTabBack(page);
		await page.waitForTimeout(500);
		const second = await page.locator('.penalty-banner').textContent();

		// The penalty amount in the banner should have grown
		expect(second).not.toBe(first);
	});
});

test.describe('Participant room — copy/paste blocking', () => {
	test('copy event is prevented inside the editor', async ({ page }) => {
		await joinRoom(page, 'CopyTester');

		// Inject a listener to detect whether copy was prevented
		const copyPrevented = await page.evaluate(() => {
			return new Promise<boolean>((resolve) => {
				document.addEventListener(
					'copy',
					(e) => {
						resolve(e.defaultPrevented);
					},
					{ once: true, capture: true },
				);
				// Trigger a copy event programmatically
				const ev = new ClipboardEvent('copy', { bubbles: true, cancelable: true });
				document.dispatchEvent(ev);
			});
		});

		// The document-level copy listener calls preventDefault
		expect(copyPrevented).toBe(true);
	});

	test('paste event is prevented inside the editor', async ({ page }) => {
		await joinRoom(page, 'PasteTester');

		const pastePrevented = await page.evaluate(() => {
			return new Promise<boolean>((resolve) => {
				document.addEventListener(
					'paste',
					(e) => {
						resolve(e.defaultPrevented);
					},
					{ once: true, capture: true },
				);
				const ev = new ClipboardEvent('paste', { bubbles: true, cancelable: true });
				document.dispatchEvent(ev);
			});
		});

		expect(pastePrevented).toBe(true);
	});

	test('Ctrl+C keyboard shortcut does not copy from editor (clipboard stays unchanged)', async ({ page, context }) => {
		await context.grantPermissions(['clipboard-read', 'clipboard-write']);
		await joinRoom(page, 'CtrlCTester');

		// Write a sentinel value to clipboard so we can detect if it changes
		await page.evaluate(() => navigator.clipboard.writeText('sentinel-value'));

		// Click into the editor and press Ctrl+C
		const editorContent = page.locator('.cm-content');
		await editorContent.click();
		await page.keyboard.press('Control+A');
		await page.keyboard.press('Control+C');

		// Wait a beat for any async clipboard write to propagate
		await page.waitForTimeout(300);
		const clipboardText = await page.evaluate(() => navigator.clipboard.readText());

		// Clipboard should still be the sentinel (copy was blocked)
		expect(clipboardText).toBe('sentinel-value');
	});
});
