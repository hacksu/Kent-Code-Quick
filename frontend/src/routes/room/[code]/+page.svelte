<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';
	import { createRoomStore } from '$lib/room.svelte';
	import Timer from '$lib/components/Timer.svelte';
	import Editor from '$lib/components/Editor.svelte';
	import Preview from '$lib/components/Preview.svelte';
	import PenaltyBanner from '$lib/components/PenaltyBanner.svelte';

	const roomCode = page.params.code;
	const name = page.url.searchParams.get('name') ?? '';
	const role = page.url.searchParams.get('role') ?? 'participant';

	if (!name) {
		goto('/');
	}

	const store = createRoomStore(roomCode, name || 'anonymous', role);

	let html = $state('');
	let css = $state('');
	let activeTab = $state<'html' | 'css'>('html');

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
		if (activeTab === 'html') {
			html = v;
		} else {
			css = v;
		}
		store.sendCodeUpdate(html, css);
	}
</script>

<div class="room-layout">
	<div class="top-bar">
		<div class="penalty-slot">
			<PenaltyBanner penalty={store.currentPenalty} />
		</div>
		<div class="timer-slot">
			<Timer elapsed={store.elapsed} durationMs={store.durationMs} />
		</div>
	</div>

	<div class="main-area">
		<div class="editor-pane">
			<div class="tab-bar">
				<button
					type="button"
					class="tab-btn"
					class:active={activeTab === 'html'}
					onclick={() => (activeTab = 'html')}
				>
					HTML
				</button>
				<button
					type="button"
					class="tab-btn"
					class:active={activeTab === 'css'}
					onclick={() => (activeTab = 'css')}
				>
					CSS
				</button>
			</div>
			<div class="editor-wrapper">
				<Editor
					language={activeTab}
					value={activeTab === 'html' ? html : css}
					onChange={onEditorChange}
					onCopyAttempt={() => store.sendCopyAttempt()}
				/>
			</div>
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
		display: flex;
		flex-direction: column;
		overflow: hidden;
		border-right: 1px solid #ccc;
	}

	.tab-bar {
		display: flex;
		gap: 0.25rem;
		padding: 0.25rem 0.5rem;
		border-bottom: 1px solid #ccc;
		flex-shrink: 0;
	}

	.tab-btn {
		padding: 0.25rem 0.75rem;
		border: 1px solid #ccc;
		background: none;
		cursor: pointer;
		border-radius: 4px 4px 0 0;
	}

	.tab-btn.active {
		background: #eee;
		font-weight: bold;
	}

	.editor-wrapper {
		flex: 1;
		overflow: hidden;
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
