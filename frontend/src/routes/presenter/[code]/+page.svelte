<script lang="ts">
	import { page } from '$app/state';
	import { createRoomStore } from '$lib/room.svelte';
	import Timer from '$lib/components/Timer.svelte';
	import ParticipantCard from '$lib/components/ParticipantCard.svelte';

	const roomCode = page.params.code!;
	const role = page.url.searchParams.get('role') ?? 'presenter';

	const store = createRoomStore(roomCode, '', role);
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

	<div class="grid flex-1 grid-cols-[repeat(auto-fill,minmax(220px,1fr))] gap-4 overflow-y-auto p-4">
		{#each Object.values(store.participants) as participant (participant.id)}
			<div>
				<ParticipantCard {participant} />
			</div>
		{/each}
	</div>
</div>
