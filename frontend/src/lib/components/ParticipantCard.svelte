<script lang="ts">
	import Preview from './Preview.svelte';
	import type { Participant } from '$lib/game.svelte';

	let {
		participant,
		paused = false,
	}: {
		participant: Pick<Participant, 'name' | 'html' | 'css' | 'js' | 'submitted_at' | 'penalty_ms' | 'copy_attempt_count'>;
		paused?: boolean;
	} = $props();

	let displayedHtml = $state('');
	let displayedCss = $state('');
	let displayedJs = $state('');

	$effect(() => {
		if (paused) return;
		displayedHtml = participant.html;
		displayedCss = participant.css;
		displayedJs = participant.js;
	});
</script>

<div class="flex h-full w-full flex-col overflow-hidden bg-white/5">
	<div data-testid="preview-wrapper" class="min-h-0 flex-1 overflow-hidden">
		<Preview html={displayedHtml} css={displayedCss} js={displayedJs} />
	</div>
	<div class="flex shrink-0 items-center gap-1.5 border-t border-white/10 bg-hacksu-grey px-2 py-1">
		<span data-testid="participant-name" class="min-w-0 flex-1 truncate text-sm font-medium text-gray-200">{participant.name}</span>
		{#if participant.submitted_at !== null}
			<span data-testid="submitted-badge" class="shrink-0 rounded bg-hacksu-green px-1.5 py-0.5 text-xs text-white">submitted</span>
		{/if}
		{#if participant.copy_attempt_count > 0}
			<span class="shrink-0 rounded bg-orange-500 px-1.5 py-0.5 text-xs text-white">{participant.copy_attempt_count}cp</span>
		{/if}
		{#if participant.penalty_ms > 0}
			<span class="shrink-0 rounded bg-red-600 px-1.5 py-0.5 text-xs text-white">-{Math.round(participant.penalty_ms / 1000)}s</span>
		{/if}
	</div>
</div>
