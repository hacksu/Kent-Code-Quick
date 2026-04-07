import { defineConfig } from 'vitest/config';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import path from 'path';

export default defineConfig({
	plugins: [svelte({ hot: false })],
	resolve: {
		alias: {
			'$app/navigation': path.resolve(__dirname, 'src/__mocks__/app-navigation.ts'),
		},
		conditions: ['browser'],
	},
	test: {
		environment: 'happy-dom',
		globals: true,
	},
});
