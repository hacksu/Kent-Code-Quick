<script lang="ts">
	import type { PenaltyPayload } from '$lib/room.svelte';

	const PENALTY_STEPS = [5, 25, 60, 120, 240, 480, 960];

	let { penalty }: { penalty: PenaltyPayload | null } = $props();

	let visible = $state(false);
	let timer: ReturnType<typeof setTimeout> | null = null;

	$effect(() => {
		if (penalty) {
			visible = true;
			if (timer) clearTimeout(timer);
			timer = setTimeout(() => {
				visible = false;
			}, 4000);
		}
		return () => {
			if (timer) clearTimeout(timer);
		};
	});

	const nextPenalty = $derived.by(() => {
		const step = penalty?.tab_out_count ?? 0;
		return PENALTY_STEPS[Math.min(step, PENALTY_STEPS.length - 1)];
	});
</script>

{#if visible && penalty}
	<div class="penalty-banner" role="alert">
		<span class="penalty-msg">
			Tab out detected! Total penalty: {penalty.penalty_ms / 1000}s
			(tab-out #{penalty.tab_out_count}). Next: {nextPenalty}s
		</span>
	</div>
{/if}

<style>
	.penalty-banner {
		background: #b91c1c;
		color: white;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.875rem;
	}
</style>
