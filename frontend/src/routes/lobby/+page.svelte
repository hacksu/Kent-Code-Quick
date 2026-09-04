<script lang="ts">
	import { onMount } from 'svelte';
	import { io, type Socket } from 'socket.io-client';
	import { loadToken, saveToken } from '$lib/store';
	import kcqLogo from '$lib/assets/images/kcq_logo.svg';
	import ParticleBackground from '$lib/components/ParticleBackground.svelte';
	import PenaltyRules from '$lib/components/PenaltyRules.svelte';

	let lobbyCount = $state(0);
	let locked = $state(false);
	let username = $state('');
	let socket: Socket;

	onMount(() => {
		fetch('/api/auth/me').then(async (resp) => {
			if (!resp.ok) { window.location.href = '/'; return; }
			const { discord_username: name } = await resp.json();
			username = name;

			socket = io({ autoConnect: false });
			const storedToken = loadToken();

			socket.on('connect', () => {
				socket.emit('join_lobby', { name, token: storedToken ?? undefined });
			});
			socket.on('token_assigned', ({ token }: { token: string }) => { saveToken(token); });
			socket.on('lobby_update', ({ lobby_count }: { lobby_count: number }) => { lobbyCount = lobby_count; });
			socket.on('game_start', ({ token }: { token: string }) => { saveToken(token); window.location.href = '/play'; });
			socket.on('game_locked', () => { locked = true; });
			socket.connect();
		});

		return () => { if (socket) socket.disconnect(); };
	});
</script>

<ParticleBackground />

<div class="relative z-10 flex min-h-screen flex-col items-center justify-center gap-8 p-4 text-white">
	<img class="w-[34vw] max-w-[260px]" src={kcqLogo} alt="Kent Code Quick" />
	{#if locked}
		<div class="text-center">
			<p class="text-xl font-semibold text-gray-300">Game in progress</p>
			<p class="mt-2 text-sm text-gray-500">Check back when the next round starts.</p>
			<a href="/" data-sveltekit-reload class="mt-4 inline-block text-sm text-hacksu-blue hover:underline">Back to home</a>
		</div>
	{:else}
		<div class="text-center">

			<h1 class="text-2xl font-bold">Waiting for the admin to start</h1>
			{#if username}
				<p class="mt-1 text-base font-medium text-brand">{username}</p>
			{/if}
			<p class="mt-2 text-sm text-gray-400">
				{lobbyCount > 0 ? `${lobbyCount} player${lobbyCount !== 1 ? 's' : ''} in the lobby` : "You're the first one here!"}
			</p>
		</div>
		<PenaltyRules />
	{/if}
</div>

