<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/state';
	import { createRoomStore } from '$lib/room.svelte';
	import Timer from '$lib/components/Timer.svelte';
	import ParticipantCard from '$lib/components/ParticipantCard.svelte';

	const roomCode = page.params.code!;
	const role = page.url.searchParams.get('role') ?? 'presenter';

	const store = createRoomStore(roomCode, '', role);

	let gridEl: HTMLDivElement;
	let visibleTokens = $state(new Set<string>());

	onMount(() => {
		const io = new IntersectionObserver(
			(entries) => {
				for (const entry of entries) {
					const token = (entry.target as HTMLElement).dataset.token;
					if (!token) continue;
					if (entry.isIntersecting) visibleTokens.add(token);
					else visibleTokens.delete(token);
				}
				// trigger reactivity
				visibleTokens = new Set(visibleTokens);
			},
			{ root: gridEl, rootMargin: '100px' }
		);

		// Watch for cards being added/removed as participants join/leave
		const mo = new MutationObserver((mutations) => {
			for (const m of mutations) {
				for (const node of m.addedNodes) {
					if (node instanceof HTMLElement && node.dataset.token) io.observe(node);
				}
				for (const node of m.removedNodes) {
					if (node instanceof HTMLElement && node.dataset.token) io.unobserve(node);
				}
			}
		});
		mo.observe(gridEl, { childList: true });

		// Observe cards already in the DOM at mount time
		for (const el of gridEl.querySelectorAll('[data-token]')) {
			io.observe(el);
		}

		return () => {
			io.disconnect();
			mo.disconnect();
		};
	});
</script>

<div class="flex h-screen flex-col overflow-hidden">
	<header class="flex shrink-0 items-center justify-between border-b border-gray-300 px-4 py-2">
		<div>
			<Timer elapsed={store.elapsed} durationMs={store.durationMs} />
		</div>
		{#if role === 'admin'}
			<button type="button" onclick={() => store.sendEndEvent()}>
				End Event
			</button>
		{/if}
	</header>

	<div
		bind:this={gridEl}
		class="grid flex-1 grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4 overflow-y-auto p-4"
	>
		{#each Object.entries(store.participants) as [token, participant] (participant.id)}
			<div data-token={token}>
				<ParticipantCard {participant} paused={!visibleTokens.has(token)} />
			</div>
		{/each}
	</div>
</div>
