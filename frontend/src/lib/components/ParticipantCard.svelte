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

<div class="participant-card">
	<div class="preview-wrapper">
		<Preview html={displayedHtml} css={displayedCss} />
	</div>
	<div class="info">
		<span class="name">{participant.name}</span>
		{#if participant.submitted_at !== null}
			<span class="badge">submitted</span>
		{/if}
		{#if participant.copy_attempt_count > 0}
			<span class="badge copy-badge">{participant.copy_attempt_count} copy</span>
		{/if}
	</div>
</div>

<style>
	.participant-card {
		display: flex;
		flex-direction: column;
		width: 200px;
	}
	.preview-wrapper {
		width: 100%;
		aspect-ratio: 16 / 9;
		overflow: hidden;
		transform-origin: top left;
	}
	.info {
		display: flex;
		align-items: center;
		gap: 0.5rem;
		padding: 0.25rem 0;
	}
	.badge {
		font-size: 0.75rem;
		background: green;
		color: white;
		padding: 0.1rem 0.4rem;
		border-radius: 4px;
	}
	.copy-badge {
		background: orange;
	}
</style>
