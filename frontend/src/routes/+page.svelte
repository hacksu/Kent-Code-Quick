<script lang="ts">
	import { onMount } from 'svelte';
	import kcqLogo from '$lib/assets/images/kcq_logo.png';
	import discordIcon from '$lib/assets/images/logos/discord.svg';
	import ParticleBackground from '$lib/components/ParticleBackground.svelte';
	import Footer from '$lib/components/Footer.svelte';

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
					class="mt-4 flex w-full cursor-pointer items-center justify-center gap-3 rounded-lg bg-hacksu-green px-4 py-3.5 text-base font-bold text-white transition-colors hover:bg-hacksu-green/90"
				>
					<img src={discordIcon} alt="" class="h-6 w-6 brightness-0 invert" />
					Login with Discord
				</button>
			</div>
		</div>

		<Footer />
	</div>
{/if}
