<script lang="ts">
	import { onMount } from 'svelte';

	let status = $state('Completing login...');

	onMount(async () => {
		const params = new URLSearchParams(window.location.search);
		const code = params.get('code');
		if (!code) {
			status = 'Login failed: missing code.';
			return;
		}

		const redirectUri = `${window.location.origin}/auth/callback`;
		const url = `/api/auth/exchange?code=${encodeURIComponent(code)}&redirect_uri=${encodeURIComponent(redirectUri)}`;
		try {
			const resp = await fetch(url, { cache: 'no-store' });
			if (!resp.ok) {
				const err = await resp.json().catch(() => ({}));
				status = `Login failed: ${err.error ?? resp.status}`;
				return;
			}
			const data = await resp.json();
			window.location.replace(data.is_admin ? '/admin' : '/lobby');
		} catch (e: any) {
			status = `Login failed: ${e?.message ?? e}`;
		}
	});
</script>

<div class="flex min-h-screen items-center justify-center bg-hacksu-grey text-white">
	<p class="text-sm text-gray-400">{status}</p>
</div>
