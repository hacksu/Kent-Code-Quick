<script lang="ts">
	import type { Participant } from '$lib/game.svelte';
	import Preview from './Preview.svelte';
	import Editor from './Editor.svelte';

	let {
		participant,
		index,
		total,
		onPrev,
		onNext,
		onClose,
	}: {
		participant: Pick<Participant, 'name' | 'html' | 'css' | 'js' | 'submitted_at' | 'tab_out_count' | 'copy_attempt_count'>;
		index: number;
		total: number;
		onPrev: () => void;
		onNext: () => void;
		onClose: () => void;
	} = $props();

	let view = $state<'preview' | 'code'>('preview');
	let codeTab = $state<'html' | 'css' | 'js'>('html');

	const codeValue = $derived(
		codeTab === 'html' ? participant.html :
		codeTab === 'css' ? participant.css : participant.js
	);

	const tabClass = (active: boolean) =>
		`cursor-pointer rounded px-3 py-1 text-sm font-medium transition-colors ${active ? 'bg-white/15 text-white' : 'text-gray-400 hover:text-white'}`;
</script>

<div class="fixed inset-0 z-50 flex flex-col bg-hacksu-grey" data-testid="participant-focus">
	<header class="flex shrink-0 items-center justify-between gap-4 border-b border-white/10 px-4 py-3">
		<button
			type="button"
			data-testid="focus-prev"
			onclick={onPrev}
			disabled={total <= 1}
			aria-label="Previous project"
			class="rounded border border-white/20 px-3 py-1.5 text-sm font-medium text-white hover:bg-white/10 disabled:opacity-30"
		>Prev</button>

		<div class="flex min-w-0 flex-col items-center gap-2 text-center">
			<span class="truncate text-xl font-bold text-white" data-testid="focus-name">{participant.name}</span>
			<span class="text-sm text-gray-400" data-testid="focus-position">{index + 1} / {total}</span>
		</div>

		<div class="flex items-center gap-2">
			<div class="flex overflow-hidden rounded border border-white/20 text-sm">
				<button
					type="button"
					onclick={() => (view = 'preview')}
					class="px-3 py-1.5 font-medium transition-colors {view === 'preview' ? 'bg-white/15 text-white' : 'text-gray-400 hover:text-white'}"
				>Preview</button>
				<button
					type="button"
					onclick={() => (view = 'code')}
					class="border-l border-white/20 px-3 py-1.5 font-medium transition-colors {view === 'code' ? 'bg-white/15 text-white' : 'text-gray-400 hover:text-white'}"
				>Code</button>
			</div>
			<button
				type="button"
				data-testid="focus-next"
				onclick={onNext}
				disabled={total <= 1}
				aria-label="Next project"
				class="rounded border border-white/20 px-3 py-1.5 text-sm font-medium text-white hover:bg-white/10 disabled:opacity-30"
			>Next</button>
			<button
				type="button"
				data-testid="focus-close"
				onclick={onClose}
				aria-label="Back to grid"
				class="rounded border border-white/20 px-3 py-1.5 text-sm font-medium text-white hover:bg-white/10"
			>Close</button>
		</div>
	</header>

	{#if view === 'preview'}
		<div class="min-h-0 flex-1 overflow-hidden bg-white">
			<Preview html={participant.html} css={participant.css} js={participant.js} />
		</div>
	{:else}
		<div class="flex shrink-0 gap-1 border-b border-white/10 bg-hacksu-grey px-2 py-1">
			<button type="button" class={tabClass(codeTab === 'html')} onclick={() => (codeTab = 'html')}>HTML</button>
			<button type="button" class={tabClass(codeTab === 'css')} onclick={() => (codeTab = 'css')}>CSS</button>
			<button type="button" class={tabClass(codeTab === 'js')} onclick={() => (codeTab = 'js')}>JS</button>
		</div>
		<div class="min-h-0 flex-1 overflow-hidden">
			<Editor
				language={codeTab}
				value={codeValue}
				readonly={true}
				blockCopyPaste={false}
				onChange={() => {}}
			/>
		</div>
	{/if}
</div>
