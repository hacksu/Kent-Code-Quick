<script lang="ts">
	let { html, css }: { html: string; css: string } = $props();

	let previousUrl = $state<string | null>(null);

	const previewUrl = $derived.by(() => {
		if (previousUrl) {
			URL.revokeObjectURL(previousUrl);
		}
		const doc = `<!DOCTYPE html><html><head><style>${css}</style></head><body>${html}</body></html>`;
		const blob = new Blob([doc], { type: 'text/html' });
		const url = URL.createObjectURL(blob);
		previousUrl = url;
		return url;
	});
</script>

<iframe sandbox="allow-scripts" src={previewUrl} title="preview" class="w-full h-full border-none" />
