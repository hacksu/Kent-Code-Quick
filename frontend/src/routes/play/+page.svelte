<script lang="ts">
	import { goto } from '$app/navigation';
	import { createPlayStore } from '$lib/game.svelte';
	import { loadToken } from '$lib/store';
	import Timer from '$lib/components/Timer.svelte';
	import Editor from '$lib/components/Editor.svelte';
	import Preview from '$lib/components/Preview.svelte';
	import PenaltyBanner from '$lib/components/PenaltyBanner.svelte';

	const token = loadToken();
	if (!token) {
		goto('/');
	}

	const store = createPlayStore(token!);

	let html = $state('');
	let css = $state('');
	let js = $state('');
	let activeTab = $state<'html' | 'css' | 'js'>('html');
	let docsOpen = $state(false);

	const frozen = $derived(store.hasSubmitted || store.eventEnded);

	const DOCS_URL = ((import.meta.env.PUBLIC_DEVDOCS_URL as string | undefined) ?? 'http://localhost:9292') + '/';

	$effect(() => {
		if (html || css || js) return;
		const me = store.myParticipant;
		if (!me) return;
		html = me.html;
		css = me.css;
		js = me.js;
	});

	$effect(() => {
		function handleVisibilityChange() {
			if (document.hidden) store.sendTabOut();
		}
		function handleBlur() {
			// window.blur also fires when focus moves into one of our own iframes
			// (the docs panel or the preview pane). That isn't a tab-out, so ignore
			// it — only penalize when focus left the page entirely (alt+tab to another
			// app or window), in which case activeElement is not an iframe.
			if (document.activeElement?.tagName === 'IFRAME') return;
			store.sendTabOut();
		}
		document.addEventListener('visibilitychange', handleVisibilityChange);
		window.addEventListener('blur', handleBlur);
		return () => {
			document.removeEventListener('visibilitychange', handleVisibilityChange);
			window.removeEventListener('blur', handleBlur);
		};
	});

	function onEditorChange(v: string) {
		if (frozen) return;
		if (activeTab === 'html') { html = v; }
		else if (activeTab === 'css') { css = v; }
		else { js = v; }
		store.sendCodeUpdate(html, css, js);
	}
</script>

<div class="room-layout grid h-screen grid-rows-[auto_1fr_auto_auto] overflow-hidden">
	<div class="top-bar flex items-center justify-between border-b border-white/10 bg-hacksu-grey px-4 py-2">
		<div class="penalty-slot">
			<PenaltyBanner penalty={store.currentPenalty} />
		</div>
		<div class="timer-slot">
			<Timer elapsed={store.elapsed} durationMs={store.durationMs} />
		</div>
	</div>

	<div class="main-area grid grid-cols-2 overflow-hidden">
		<div class="editor-pane flex flex-col overflow-hidden border-r border-gray-300">
			<div class="tab-bar flex shrink-0 gap-1 border-b border-white/10 bg-hacksu-grey px-2 py-1">
				<button
					type="button"
					class={`tab-btn cursor-pointer rounded px-3 py-1 text-sm font-medium transition-colors ${activeTab === 'html' ? 'active bg-white/15 text-white' : 'text-gray-400 hover:text-white'}`}
					onclick={() => (activeTab = 'html')}
				>HTML</button>
				<button
					type="button"
					class={`tab-btn cursor-pointer rounded px-3 py-1 text-sm font-medium transition-colors ${activeTab === 'css' ? 'active bg-white/15 text-white' : 'text-gray-400 hover:text-white'}`}
					onclick={() => (activeTab = 'css')}
				>CSS</button>
				<button
					type="button"
					class={`tab-btn cursor-pointer rounded px-3 py-1 text-sm font-medium transition-colors ${activeTab === 'js' ? 'active bg-white/15 text-white' : 'text-gray-400 hover:text-white'}`}
					onclick={() => (activeTab = 'js')}
				>JS</button>
			</div>
			<div class="editor-wrapper flex-1 overflow-hidden">
				<Editor
					language={activeTab}
					value={activeTab === 'html' ? html : activeTab === 'css' ? css : js}
					readonly={frozen}
					onChange={onEditorChange}
					onCopyAttempt={() => store.sendCopyAttempt()}
				/>
			</div>
		</div>
		<div class="preview-pane overflow-hidden">
			<Preview {html} {css} {js} />
		</div>
	</div>

	<div class="docs-panel h-[300px] overflow-hidden border-t border-gray-300 {docsOpen ? '' : 'hidden'}">
		<iframe src={DOCS_URL} title="Documentation" class="h-full w-full border-none" sandbox="allow-scripts allow-same-origin allow-forms"></iframe>
	</div>

	<div class="bottom-bar flex items-center justify-between border-t border-white/10 bg-hacksu-grey px-4 py-2">
		<button
			type="button"
			class="rounded border border-white/20 px-3 py-1 text-sm text-gray-400 hover:border-white/40 hover:text-white"
			onclick={() => (docsOpen = !docsOpen)}
		>{docsOpen ? 'Hide Docs' : 'Show Docs'}</button>

		<div class="submit-slot">
			{#if store.eventEnded}
				<span class="text-sm text-gray-400">Event ended</span>
			{:else if store.hasSubmitted}
				<span class="rounded bg-hacksu-green/20 px-3 py-1 text-sm font-medium text-hacksu-green">Submitted</span>
			{:else}
				<button
					type="button"
					class="submit-btn rounded bg-hacksu-green px-4 py-1.5 text-sm font-semibold text-white hover:opacity-90"
					onclick={() => store.sendSubmit()}
				>Submit</button>
			{/if}
		</div>
	</div>
</div>
