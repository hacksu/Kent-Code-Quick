<script lang="ts">
	let { elapsed, durationMs }: { elapsed: number; durationMs: number } = $props();

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
</script>

<span class={`tabular-nums${overtime ? ' text-red-600' : ''}`}>{display}</span>
