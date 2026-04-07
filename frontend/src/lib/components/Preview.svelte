<script lang="ts">
	let { html, css }: { html: string; css: string } = $props();

	const previewUrl = $derived.by(() => {
		const doc = `<!DOCTYPE html><html><head><style>${css}</style></head><body>${html}</body></html>`;
		const blob = new Blob([doc], { type: 'text/html' });
		return URL.createObjectURL(blob);
	});

	$effect(() => {
		const url = previewUrl;
		return () => URL.revokeObjectURL(url);
	});
</script>

<iframe sandbox="allow-scripts" src={previewUrl} title="preview" class="w-full h-full border-none"></iframe>
