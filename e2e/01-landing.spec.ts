import { test, expect } from '@playwright/test';

test.describe('Landing page', () => {
	test('renders the title and join form', async ({ page }) => {
		await page.goto('/');
		await expect(page.locator('h1')).toContainText('Kent Code Quick');
		await expect(page.locator('#room-code')).toBeVisible();
		await expect(page.locator('#name')).toBeVisible();
		await expect(page.locator('button[type="submit"]')).toBeVisible();
	});

	test('Join button is disabled when fields are empty', async ({ page }) => {
		await page.goto('/');
		await expect(page.locator('button[type="submit"]')).toBeDisabled();
	});

	test('Join button enables once room code and name are filled', async ({ page }) => {
		await page.goto('/');
		await page.fill('#room-code', 'TEST');
		await page.fill('#name', 'Alice');
		await expect(page.locator('button[type="submit"]')).toBeEnabled();
	});

	test('Admin role shows secret field', async ({ page }) => {
		await page.goto('/');
		await page.selectOption('#role', 'admin');
		await expect(page.locator('#secret')).toBeVisible();
	});

	test('Admin role requires secret to enable join', async ({ page }) => {
		await page.goto('/');
		await page.fill('#room-code', 'TEST');
		await page.fill('#name', 'Boss');
		await page.selectOption('#role', 'admin');
		await expect(page.locator('button[type="submit"]')).toBeDisabled();
		await page.fill('#secret', 'anything');
		await expect(page.locator('button[type="submit"]')).toBeEnabled();
	});

	test('navigates to /room/<CODE> after joining as participant', async ({ page }) => {
		await page.goto('/');
		await page.fill('#room-code', 'land01');
		await page.fill('#name', 'Alice');
		await page.click('button[type="submit"]');
		await expect(page).toHaveURL(/\/room\/LAND01/);
	});

	test('navigates to /presenter/<CODE> after joining as presenter', async ({ page }) => {
		await page.goto('/');
		await page.fill('#room-code', 'land01');
		await page.fill('#name', 'Host');
		await page.selectOption('#role', 'presenter');
		await page.click('button[type="submit"]');
		await expect(page).toHaveURL(/\/presenter\/LAND01/);
	});
});
