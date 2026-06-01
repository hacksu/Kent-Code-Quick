<script lang="ts">
	import type { Participant } from '$lib/game.svelte';
	import ParticipantCard from './ParticipantCard.svelte';

	let {
		participant,
		index,
		total,
		onPrev,
		onNext,
		onClose,
	}: {
		participant: Pick<Participant, 'name' | 'html' | 'css' | 'js' | 'submitted_at' | 'penalty_ms' | 'copy_attempt_count'>;
		index: number;
		total: number;
		onPrev: () => void;
		onNext: () => void;
		onClose: () => void;
	} = $props();
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

		<div class="flex min-w-0 flex-col items-center text-center">
			<span class="truncate text-xl font-bold text-white" data-testid="focus-name">{participant.name}</span>
			<span class="text-sm text-gray-400" data-testid="focus-position">{index + 1} / {total}</span>
		</div>

		<div class="flex items-center gap-2">
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

	<div class="min-h-0 flex-1 overflow-hidden">
		<ParticipantCard {participant} paused={false} />
	</div>
</div>
