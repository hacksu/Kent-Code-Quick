<script lang="ts">
	import { onMount } from 'svelte';
	import kcqLogo from '$lib/assets/images/kcq_logo.png';
	import discordIcon from '$lib/assets/images/logos/discord.svg';
	import ParticleBackground from '$lib/components/ParticleBackground.svelte';
	import { startDiscordLogin } from '$lib/discord-auth';
	import { destinationFor } from '$lib/auth-gate';

	let checking = $state(true);
	let clientId = $state('');

	const configError = $derived(!checking && clientId === '');

	onMount(async () => {
		try {
			const resp = await fetch('/api/auth/me');
			if (resp.ok) {
				window.location.replace(destinationFor(await resp.json()));
				return;
			}
		} catch {
			// network error, fall through and offer the button
		}

		try {
			const cfg = await fetch('/api/config');
			if (cfg.ok) clientId = (await cfg.json()).discord_client_id ?? '';
		} catch {
			// leave clientId empty; the message below explains the problem
		}
		checking = false;
	});
</script>

<svelte:head>
	<title>Sign in - Kent Code Quick</title>
	<meta name="robots" content="noindex" />
</svelte:head>

<ParticleBackground />

<div class="relative z-10 flex min-h-screen flex-col items-center justify-center gap-6 p-4 text-center text-white">
	{#if checking}
		<div class="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-hacksu-green"></div>
	{:else}
		<img class="w-[clamp(88px,15vw,126px)]" src={kcqLogo} alt="Kent Code Quick" />
		<h1 class="font-display text-2xl font-bold tracking-wide uppercase">Sign in</h1>

		<button
			type="button"
			data-testid="discord-login"
			disabled={configError}
			onclick={() => startDiscordLogin(clientId)}
			class="mt-1 flex cursor-pointer items-center gap-2.5 rounded-lg bg-hacksu-green px-5 py-3.5 text-[0.95rem] font-medium text-[#07130d] transition-colors hover:bg-hacksu-green/90 disabled:cursor-not-allowed disabled:opacity-40"
		>
			<img src={discordIcon} alt="" class="h-5 w-5" />
			Continue with Discord
		</button>

		{#if configError}
			<p class="text-sm text-red-400" data-testid="config-error">
				Sign-in is unavailable: the server has no Discord client ID configured.
			</p>
		{/if}

		<a href="/" data-sveltekit-reload class="text-sm text-hacksu-blue hover:underline">Back to home</a>
	{/if}
</div>
