<script lang="ts">
	let { elapsed, durationMs, paused = false }: { elapsed: number; durationMs: number; paused?: boolean } = $props();

	const remaining = $derived(durationMs - elapsed);
	const overtime = $derived(remaining < 0);

	const display = $derived.by(() => {
		const abs = Math.abs(remaining);
		const totalSeconds = Math.floor(abs / 1000);
		const minutes = Math.floor(totalSeconds / 60);
		const seconds = totalSeconds % 60;
		const formatted = `${minutes}:${String(seconds).padStart(2, '0')}`;
		return overtime ? `-${formatted}` : formatted;
	});

	const colorClass = $derived(paused ? 'text-yellow-400 paused' : overtime ? 'text-red-500 overtime' : 'text-hacksu-blue');
</script>

<span class={`tabular-nums font-medium ${colorClass}`}>{display}</span>
