<script lang="ts">
	import { onMount } from 'svelte';
	import kcqLogo from '$lib/assets/images/kcq_logo.png';
	import discordIcon from '$lib/assets/images/logos/discord.svg';
	import ParticleBackground from '$lib/components/ParticleBackground.svelte';
	import Footer from '$lib/components/Footer.svelte';

	let checking = $state(true);
	let clientId = $state('');
	let configError = $state(false);

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

		try {
			const cfg = await fetch('/api/config');
			if (cfg.ok) clientId = (await cfg.json()).discord_client_id ?? '';
		} catch {
			// leave clientId empty; the button below explains the problem
		}
		configError = clientId === '';
		checking = false;
	});

	function randomState(): string {
		if (typeof crypto !== 'undefined') {
			if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
			if (typeof crypto.getRandomValues === 'function') {
				const bytes = crypto.getRandomValues(new Uint8Array(16));
				return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
			}
		}
		return `${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`;
	}

	function login() {
		if (!clientId) return;
		const redirectUri = `${window.location.origin}/auth/callback`;
		const state = randomState();
		sessionStorage.setItem('oauthState', state);
		const params = new URLSearchParams({
			client_id: clientId,
			redirect_uri: redirectUri,
			response_type: 'code',
			scope: 'identify guilds.members.read',
			state,
		});
		window.location.href = `https://discord.com/oauth2/authorize?${params}`;
	}
</script>

<ParticleBackground />

{#if checking}
	<div class="relative z-10 flex min-h-screen items-center justify-center">
		<div class="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-hacksu-green"></div>
	</div>
{:else}
	<div class="relative z-10 flex min-h-screen flex-col">
		<div class="flex flex-1 flex-col items-center justify-center px-4 text-white">
			<img class="mb-8 w-[40vw] max-w-[360px]" src={kcqLogo} alt="Kent Code Quick" />

			<h1 class="text-center text-3xl font-bold sm:text-4xl">Kent Code Quick</h1>
			<p class="mt-3 max-w-md text-center text-lg text-gray-300">
				HacKSU's live front-end coding competition.
			</p>

			<div class="mt-10 w-full max-w-sm">
				<button
					type="button"
					onclick={login}
					disabled={configError}
					class="mt-4 flex w-full cursor-pointer items-center justify-center gap-3 rounded-lg bg-hacksu-green px-4 py-3.5 text-base font-bold text-white transition-colors hover:bg-hacksu-green/90 disabled:cursor-not-allowed disabled:opacity-40"
				>
					<img src={discordIcon} alt="" class="h-6 w-6 brightness-0 invert" />
					Login with Discord
				</button>
				{#if configError}
					<p class="mt-3 text-center text-sm text-red-400" data-testid="config-error">
						Login is unavailable: the server has no Discord client ID configured.
					</p>
				{/if}
			</div>
		</div>

		<Footer />
	</div>
{/if}
