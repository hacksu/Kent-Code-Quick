<script lang="ts">
	let { html, css }: { html: string; css: string } = $props();

	let iframe: HTMLIFrameElement;

	$effect(() => {
		if (!iframe?.contentDocument) return;
		const doc = `<!DOCTYPE html><html><head><meta charset="utf-8"><style>
			* { box-sizing: border-box; }
			body { margin: 8px; font-family: sans-serif; }
			${css}
		</style></head><body>${html}</body></html>`;
		iframe.contentDocument.open();
		iframe.contentDocument.write(doc);
		iframe.contentDocument.close();
	});
</script>

<iframe bind:this={iframe} title="preview" class="w-full h-full border-none bg-white"></iframe>
