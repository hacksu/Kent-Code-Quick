<script lang="ts">
	import { page } from '$app/state';
	import { createRoomStore } from '$lib/room.svelte';
	import Timer from '$lib/components/Timer.svelte';
	import ParticipantCard from '$lib/components/ParticipantCard.svelte';

	const roomCode = page.params.code;
	const role = page.url.searchParams.get('role') ?? 'presenter';

	const store = createRoomStore(roomCode, '', role);
</script>

<div class="presenter-layout">
	<header class="header-bar">
		<div class="timer-slot">
			<Timer elapsed={store.elapsed} durationMs={store.durationMs} />
		</div>
		{#if role === 'admin'}
			<button type="button" class="end-event-btn" onclick={() => store.sendEndEvent()}>
				End Event
			</button>
		{/if}
	</header>

	<div class="participant-grid">
		{#each Object.values(store.participants) as participant (participant.id)}
			<div class="participant-item">
				<ParticipantCard {participant} />
			</div>
		{/each}
	</div>
</div>

<style>
	.presenter-layout {
		display: flex;
		flex-direction: column;
		height: 100vh;
		overflow: hidden;
	}

	.header-bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem 1rem;
		border-bottom: 1px solid #ccc;
		flex-shrink: 0;
	}

	.participant-grid {
		flex: 1;
		display: grid;
		grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
		gap: 1rem;
		padding: 1rem;
		overflow-y: auto;
	}
</style>
