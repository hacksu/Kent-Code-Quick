<script lang="ts">
	import { onMount } from 'svelte';
	import { createWatchStore } from '$lib/game.svelte';
	import kcqLogo from '$lib/assets/images/kcq_logo.png';
	import ParticipantCard from '$lib/components/ParticipantCard.svelte';
	import ParticipantFocus from '$lib/components/ParticipantFocus.svelte';
	import Timer from '$lib/components/Timer.svelte';

	let authed = $state(false);
	const store = createWatchStore();

	// Ordered participant entries - shared by the grid and the focus navigation
	// so "next/prev" matches the on-screen layout order.
	const entries = $derived(Object.entries(store.participants));

	const cols = $derived(() => {
		const n = entries.length;
		return n <= 1 ? 1 : Math.ceil(Math.sqrt(n));
	});

	// --- Focus / flip-through mode ---
	let focusedToken = $state<string | null>(null);

	const focusedIndex = $derived(
		focusedToken === null ? -1 : entries.findIndex(([tok]) => tok === focusedToken)
	);

	// If the focused participant disappears (game reset, etc.), exit focus mode.
	$effect(() => {
		if (focusedToken !== null && focusedIndex === -1) {
			focusedToken = null;
		}
	});

	function focusAt(i: number) {
		const n = entries.length;
		if (n === 0) {
			focusedToken = null;
			return;
		}
		const wrapped = ((i % n) + n) % n;
		focusedToken = entries[wrapped][0];
	}

	function focusNext() {
		if (focusedIndex >= 0) focusAt(focusedIndex + 1);
	}

	function focusPrev() {
		if (focusedIndex >= 0) focusAt(focusedIndex - 1);
	}

	function closeFocus() {
		focusedToken = null;
	}

	// Keyboard navigation while focused: Left/Right arrows to flip, Esc to return to grid.
	$effect(() => {
		if (focusedToken === null) return;
		function onKey(e: KeyboardEvent) {
			if (e.key === 'ArrowRight') { e.preventDefault(); focusNext(); }
			else if (e.key === 'ArrowLeft') { e.preventDefault(); focusPrev(); }
			else if (e.key === 'Escape') { e.preventDefault(); closeFocus(); }
		}
		window.addEventListener('keydown', onKey);
		return () => window.removeEventListener('keydown', onKey);
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
		<header class="flex shrink-0 items-center justify-between border-b border-gray-700/50 bg-hacksu-grey/80 px-4 py-2 backdrop-blur-sm">
			<div class="flex items-center gap-3">
				<img src={kcqLogo} alt="Kent Code Quick" class="h-7 w-auto" />
				<Timer elapsed={store.elapsed} durationMs={store.durationMs} />
			</div>
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
			{#each entries as [tok, participant] (participant.id)}
				<div data-participant={tok} class="relative min-h-0 overflow-hidden border border-white/10">
					<ParticipantCard {participant} paused={false} />
					<button
						type="button"
						data-testid="focus-card"
						aria-label={`Focus ${participant.name}'s project`}
						onclick={() => (focusedToken = tok)}
						class="absolute inset-0 cursor-pointer transition-shadow hover:ring-2 hover:ring-inset hover:ring-white/40 focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-brand focus-visible:outline-none"
					></button>
				</div>
			{/each}
		</div>
	</div>

	{#if focusedIndex >= 0}
		<ParticipantFocus
			participant={entries[focusedIndex][1]}
			index={focusedIndex}
			total={entries.length}
			onPrev={focusPrev}
			onNext={focusNext}
			onClose={closeFocus}
		/>
	{/if}
{/if}
