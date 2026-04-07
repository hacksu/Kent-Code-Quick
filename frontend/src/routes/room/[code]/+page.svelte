<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { createRoomStore } from '$lib/room.svelte';
	import Timer from '$lib/components/Timer.svelte';
	import Editor from '$lib/components/Editor.svelte';
	import Preview from '$lib/components/Preview.svelte';

	const roomCode = page.params.code;
	const name = page.url.searchParams.get('name') ?? '';
	const role = page.url.searchParams.get('role') ?? 'participant';

	if (!name) {
		goto('/');
	}

	const store = createRoomStore(roomCode, name || 'anonymous', role);

	let html = $state('');
	let css = $state('');

	function onHtmlChange(v: string) {
		html = v;
		store.sendCodeUpdate(html, css);
	}

	function onCssChange(v: string) {
		css = v;
		store.sendCodeUpdate(html, css);
	}
</script>

<div class="room-layout">
	<div class="top-bar">
		<div class="penalty-slot"></div>
		<div class="timer-slot">
			<Timer elapsed={store.elapsed} durationMs={store.durationMs} />
		</div>
	</div>

	<div class="main-area">
		<div class="editor-pane">
			<Editor language="html" value={html} onChange={onHtmlChange} />
			<Editor language="css" value={css} onChange={onCssChange} />
		</div>
		<div class="preview-pane">
			<Preview {html} {css} />
		</div>
	</div>

	<div class="bottom-bar">
		<div class="docs-slot">
			<button type="button">Docs</button>
		</div>
		<div class="submit-slot">
			<button
				type="button"
				class="submit-btn"
				onclick={() => store.sendSubmit()}
				disabled={store.hasSubmitted}
			>
				{store.hasSubmitted ? 'Submitted' : 'Submit'}
			</button>
		</div>
	</div>
</div>

<style>
	.room-layout {
		display: grid;
		grid-template-rows: auto 1fr auto;
		height: 100vh;
		overflow: hidden;
	}

	.top-bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem 1rem;
		border-bottom: 1px solid #ccc;
	}

	.main-area {
		display: grid;
		grid-template-columns: 1fr 1fr;
		overflow: hidden;
	}

	.editor-pane {
		display: grid;
		grid-template-rows: 1fr 1fr;
		overflow: hidden;
		border-right: 1px solid #ccc;
	}

	.preview-pane {
		overflow: hidden;
	}

	.bottom-bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: 0.5rem 1rem;
		border-top: 1px solid #ccc;
	}

	.submit-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}
</style>
