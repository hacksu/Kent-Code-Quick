<script lang="ts">
	let { html, css, js }: { html: string; css: string; js: string } = $props();

	let srcdoc = $state('');
	let debounce: ReturnType<typeof setTimeout> | null = null;

	$effect(() => {
		const h = html, c = css, j = js;
		if (debounce !== null) clearTimeout(debounce);
		debounce = setTimeout(() => {
			srcdoc = `<!DOCTYPE html><html><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'unsafe-inline'; script-src 'unsafe-inline'; connect-src 'none'">
<style>* { box-sizing: border-box; } body { margin: 8px; font-family: sans-serif; } ${c}</style>
</head><body>${h}<script>${j}<\/script></body></html>`;
		}, 300);
	});
</script>

<iframe
	title="preview"
	sandbox="allow-scripts"
	referrerpolicy="no-referrer"
	{srcdoc}
	class="w-full h-full border-none bg-white"
></iframe>
