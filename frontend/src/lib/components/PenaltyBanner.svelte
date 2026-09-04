<script lang="ts">
	import type { PenaltyPayload } from '$lib/game.svelte';

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
</script>

{#if visible && penalty}
	<div class="penalty-banner rounded bg-red-700 px-3 py-1 text-sm text-white" role="alert">
		{#if penalty.type === 'copy'}
			Copy attempt detected! Total copy attempts: {penalty.count}
		{:else}
			Tab out detected! Total tab-outs: {penalty.count}
		{/if}
	</div>
{/if}
