<script lang="ts">
	import { onMount } from 'svelte';

	const DISCORD_CLIENT_ID = '1415050533281988759';

	let checking = $state(true);

	onMount(async () => {
		try {
			const resp = await fetch('/api/auth/me');
			if (resp.ok) {
				const data = await resp.json();
				window.location.replace(data.is_admin ? '/admin' : '/lobby');
				return;
			}
		} catch {
			// network error, fall through
		}
		checking = false;
	});

	function login() {
		const redirectUri = `${window.location.origin}/auth/callback`;
		const params = new URLSearchParams({
			client_id: DISCORD_CLIENT_ID,
			redirect_uri: redirectUri,
			response_type: 'code',
			scope: 'identify guilds.members.read',
		});
		window.location.href = `https://discord.com/oauth2/authorize?${params}`;
	}
</script>

{#if checking}
	<div class="flex min-h-screen items-center justify-center bg-hacksu-grey">
		<div class="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-white"></div>
	</div>
{:else}
	<div class="flex min-h-screen items-center justify-center bg-hacksu-grey p-4">
		<div class="w-full max-w-sm text-center">
			<h1 class="mb-2 text-2xl font-bold text-white">Kent Code Quick</h1>
			<p class="mb-8 text-sm text-gray-400">Sign in with Discord to continue</p>

			<button
				type="button"
				onclick={login}
				class="w-full rounded-lg bg-[#5865F2] px-4 py-3 text-sm font-semibold text-white transition-opacity hover:opacity-90"
			>
				Login with Discord
			</button>
		</div>
	</div>
{/if}
