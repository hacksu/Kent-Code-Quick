<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { createRoomStore } from '$lib/room.svelte';
	import Timer from '$lib/components/Timer.svelte';
	import Editor from '$lib/components/Editor.svelte';
	import Preview from '$lib/components/Preview.svelte';
	import PenaltyBanner from '$lib/components/PenaltyBanner.svelte';

	const roomCode = page.params.code!;
	const name = page.url.searchParams.get('name') ?? '';
	const role = page.url.searchParams.get('role') ?? 'participant';

	if (!name) {
		goto('/');
	}

	const store = createRoomStore(roomCode, name || 'anonymous', role);

	let html = $state('');
	let css = $state('');
	let activeTab = $state<'html' | 'css'>('html');

	const frozen = $derived(store.hasSubmitted || store.eventEnded);

	let docsOpen = $state(false);
	const DOCS_URL = ((import.meta.env.PUBLIC_DEVDOCS_URL as string | undefined) ?? 'http://localhost:9292') + '/';

	// When we first find our participant data (initial load or reconnect with empty state),
	// populate the local editor from the store.
	$effect(() => {
		if (html || css) return;
		if (!store.myToken) return;
		const me = store.participants[store.myToken];
		if (!me) return;
		html = me.html;
		css = me.css;
	});

	$effect(() => {
		function handleVisibilityChange() {
			if (document.hidden) {
				store.sendTabOut();
			}
		}
		document.addEventListener('visibilitychange', handleVisibilityChange);
		return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
	});

	function onEditorChange(v: string) {
		if (frozen) return;
		if (activeTab === 'html') {
			html = v;
		} else {
			css = v;
		}
		store.sendCodeUpdate(html, css);
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
				>
					HTML
				</button>
				<button
					type="button"
					class={`tab-btn cursor-pointer rounded px-3 py-1 text-sm font-medium transition-colors ${activeTab === 'css' ? 'active bg-white/15 text-white' : 'text-gray-400 hover:text-white'}`}
					onclick={() => (activeTab = 'css')}
				>
					CSS
				</button>
			</div>
			<div class="editor-wrapper flex-1 overflow-hidden">
				<Editor
					language={activeTab}
					value={activeTab === 'html' ? html : css}
					readonly={frozen}
					onChange={onEditorChange}
					onCopyAttempt={() => store.sendCopyAttempt()}
				/>
			</div>
		</div>
		<div class="preview-pane overflow-hidden">
			<Preview {html} {css} />
		</div>
	</div>

	<div class="docs-panel h-[300px] overflow-hidden border-t border-gray-300 {docsOpen ? '' : 'hidden'}">
		<iframe
			src={DOCS_URL}
			title="Documentation"
			class="h-full w-full border-none"
			sandbox="allow-scripts allow-same-origin allow-forms"
		></iframe>
	</div>

	<div class="bottom-bar flex items-center justify-between border-t border-white/10 bg-hacksu-grey px-4 py-2">
		<div class="docs-slot">
			<button
				type="button"
				class="rounded border border-white/20 px-3 py-1 text-sm text-gray-400 hover:border-white/40 hover:text-white"
				onclick={() => (docsOpen = !docsOpen)}
			>
				{docsOpen ? 'Hide Docs' : 'Show Docs'}
			</button>
		</div>
		<div class="submit-slot">
			{#if store.eventEnded}
				<span class="text-sm text-gray-400">Event ended</span>
			{:else if store.hasSubmitted}
				<span class="rounded bg-hacksu-green/20 px-3 py-1 text-sm font-medium text-hacksu-green">Submitted</span>
			{:else}
				<button
					type="button"
					class="submit-btn rounded bg-hacksu-green px-4 py-1.5 text-sm font-semibold text-white hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
					onclick={() => store.sendSubmit()}
				>
					Submit
				</button>
			{/if}
		</div>
	</div>
</div>
