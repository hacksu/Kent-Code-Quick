<script lang="ts">
	import Preview from './Preview.svelte';
	import type { Participant } from '../room.svelte';

	let {
		participant,
		throttleMs = 500,
		paused = false,
	}: {
		participant: Pick<Participant, 'name' | 'html' | 'css' | 'submitted_at' | 'penalty_ms' | 'copy_attempt_count'>;
		throttleMs?: number;
		paused?: boolean;
	} = $props();

	let displayedHtml = $state('');
	let displayedCss = $state('');
	let lastUpdate = $state(0);

	$effect(() => {
		if (paused) return;
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

<div class="participant-card flex w-[200px] flex-col overflow-hidden rounded-lg border border-white/10 bg-white/5 shadow-sm">
	<div class="preview-wrapper aspect-video w-full origin-top-left overflow-hidden bg-gray-50">
		<Preview html={displayedHtml} css={displayedCss} />
	</div>
	<div class="flex items-center gap-1.5 border-t border-white/10 px-2 py-1.5">
		<span class="name min-w-0 flex-1 truncate text-sm font-medium text-gray-200">{participant.name}</span>
		{#if participant.submitted_at !== null}
			<span class="badge shrink-0 rounded bg-hacksu-green px-1.5 py-0.5 text-xs text-white">submitted</span>
		{/if}
		{#if participant.copy_attempt_count > 0}
			<span class="badge shrink-0 rounded bg-orange-500 px-1.5 py-0.5 text-xs text-white">{participant.copy_attempt_count}cp</span>
		{/if}
	</div>
</div>
