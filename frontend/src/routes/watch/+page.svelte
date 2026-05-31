<script lang="ts">
	import { onMount } from 'svelte';
	import { createWatchStore } from '$lib/game.svelte';
	import ParticipantCard from '$lib/components/ParticipantCard.svelte';
	import Timer from '$lib/components/Timer.svelte';

	let authed = $state(false);
	const store = createWatchStore();

	const cols = $derived(() => {
		const n = Object.keys(store.participants).length;
		return n <= 1 ? 1 : Math.ceil(Math.sqrt(n));
	});

	onMount(async () => {
		const resp = await fetch('/api/auth/me');
		if (!resp.ok) {
			window.location.replace('/');
			return;
		}
		const data = await resp.json();
		if (!data.is_admin) {
			window.location.replace('/');
			return;
		}
		authed = true;
	});
</script>

{#if !authed}
	<div class="flex h-screen items-center justify-center bg-hacksu-grey text-gray-400">
		Checking authorization...
	</div>
{:else}
	<div class="flex h-screen flex-col overflow-hidden bg-hacksu-grey">
		<header class="flex shrink-0 items-center justify-between border-b border-white/10 px-4 py-2">
			<Timer elapsed={store.elapsed} durationMs={store.durationMs} />
			<div class="flex items-center gap-3">
				{#if store.gameStatus === 'active'}
					<button
						type="button"
						data-testid="end-game-btn"
						onclick={() => store.sendEndEvent()}
						class="rounded bg-red-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-red-700"
					>End Game</button>
				{:else if store.gameStatus === 'ended'}
					<span class="text-sm text-gray-400">Game ended</span>
				{:else}
					<span class="text-sm text-gray-500">Waiting for game to start</span>
				{/if}
				<a href="/admin" class="text-sm text-gray-500 hover:text-white">Admin</a>
			</div>
		</header>

		<div
			class="grid flex-1 overflow-hidden"
			style="grid-template-columns: repeat({cols()}, 1fr)"
		>
			{#each Object.entries(store.participants) as [tok, participant] (participant.id)}
				<div data-participant={tok} class="min-h-0 overflow-hidden border border-white/10">
					<ParticipantCard {participant} paused={false} />
				</div>
			{/each}
		</div>
	</div>
{/if}
