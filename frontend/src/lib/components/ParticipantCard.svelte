<script lang="ts">
	import Preview from './Preview.svelte';
	import type { Participant } from '../room.svelte';

	let {
		participant,
		throttleMs = 500,
	}: {
		participant: Pick<Participant, 'name' | 'html' | 'css' | 'submitted_at' | 'penalty_ms' | 'copy_attempt_count'>;
		throttleMs?: number;
	} = $props();

	let displayedHtml = $state('');
	let displayedCss = $state('');
	let lastUpdate = $state(0);

	$effect(() => {
		const html = participant.html;
		const css = participant.css;
		const now = Date.now();
		if (now - lastUpdate >= throttleMs) {
			displayedHtml = html;
			displayedCss = css;
			lastUpdate = now;
		}
	});
</script>

<div class="participant-card flex w-[200px] flex-col">
	<div class="preview-wrapper aspect-video w-full origin-top-left overflow-hidden">
		<Preview html={displayedHtml} css={displayedCss} />
	</div>
	<div class="flex items-center gap-2 py-1">
		<span class="name">{participant.name}</span>
		{#if participant.submitted_at !== null}
			<span class="badge rounded bg-green-600 px-1.5 py-0.5 text-xs text-white">submitted</span>
		{/if}
		{#if participant.copy_attempt_count > 0}
			<span class="badge rounded bg-orange-500 px-1.5 py-0.5 text-xs text-white">{participant.copy_attempt_count} copy</span>
		{/if}
	</div>
</div>
