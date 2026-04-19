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

<div class="grid h-screen grid-rows-[auto_1fr_auto] overflow-hidden">
	<div class="flex items-center justify-between border-b border-gray-300 px-4 py-2">
		<div>
			<PenaltyBanner penalty={store.currentPenalty} />
		</div>
		<div>
			<Timer elapsed={store.elapsed} durationMs={store.durationMs} />
		</div>
	</div>

	<div class="grid grid-cols-2 overflow-hidden">
		<div class="flex flex-col overflow-hidden border-r border-gray-300">
			<div class="flex shrink-0 gap-1 border-b border-gray-300 px-2 py-1">
				<button
					type="button"
					class={`cursor-pointer rounded-t border border-gray-300 px-3 py-1 ${activeTab === 'html' ? 'bg-gray-200 font-bold' : 'bg-transparent'}`}
					onclick={() => (activeTab = 'html')}
				>
					HTML
				</button>
				<button
					type="button"
					class={`cursor-pointer rounded-t border border-gray-300 px-3 py-1 ${activeTab === 'css' ? 'bg-gray-200 font-bold' : 'bg-transparent'}`}
					onclick={() => (activeTab = 'css')}
				>
					CSS
				</button>
			</div>
			<div class="flex-1 overflow-hidden">
				<Editor
					language={activeTab}
					value={activeTab === 'html' ? html : css}
					readonly={frozen}
					onChange={onEditorChange}
					onCopyAttempt={() => store.sendCopyAttempt()}
				/>
			</div>
		</div>
		<div class="overflow-hidden">
			<Preview {html} {css} />
		</div>
	</div>

	<div class="flex items-center justify-between border-t border-gray-300 px-4 py-2">
		<div>
			<button type="button">Docs</button>
		</div>
		<div>
			{#if store.eventEnded}
				<span class="text-sm text-gray-500">Event ended</span>
			{:else if store.hasSubmitted}
				<span class="text-sm text-green-600">Submitted</span>
			{:else}
				<button
					type="button"
					class="disabled:cursor-not-allowed disabled:opacity-50"
					onclick={() => store.sendSubmit()}
				>
					Submit
				</button>
			{/if}
		</div>
	</div>
</div>
