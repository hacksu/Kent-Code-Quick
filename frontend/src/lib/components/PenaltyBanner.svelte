<script lang="ts">
	import type { PenaltyPayload } from '$lib/game.svelte';

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
		const step = penalty?.count ?? 0;
		return PENALTY_STEPS[Math.min(step, PENALTY_STEPS.length - 1)];
	});
</script>

{#if visible && penalty}
	<div class="penalty-banner rounded bg-red-700 px-3 py-1 text-sm text-white" role="alert">
		{#if penalty.type === 'copy'}
			Copy attempt! +{PENALTY_STEPS[Math.min((penalty.count - 1), PENALTY_STEPS.length - 1)]}s penalty.
		{:else}
			Tab out detected! +{PENALTY_STEPS[Math.min((penalty.count - 1), PENALTY_STEPS.length - 1)]}s penalty.
		{/if}
		Total: {penalty.penalty_ms / 1000}s. Next: {nextPenalty}s
	</div>
{/if}
