import { defineConfig, devices } from '@playwright/test';
import path from 'path';

const backendPython = path.join(__dirname, 'backend', '.venv', 'Scripts', 'python.exe');
const backendApp = path.join(__dirname, 'backend', 'app.py');

export default defineConfig({
	testDir: './e2e',
	fullyParallel: false,
	forbidOnly: !!process.env.CI,
	retries: process.env.CI ? 2 : 0,
	workers: 1,
	reporter: 'list',
	timeout: 30_000,
	use: {
		baseURL: 'http://localhost:5001',
		trace: 'on-first-retry',
	},
	projects: [
		{
			name: 'chromium',
			use: { ...devices['Desktop Chrome'] },
		},
	],
	webServer: {
		command: `"${backendPython}" "${backendApp}"`,
		url: 'http://localhost:5001',
		reuseExistingServer: !process.env.CI,
		timeout: 15_000,
		env: {
			ADMIN_SECRET: 'e2e-test-secret',
		},
	},
});
