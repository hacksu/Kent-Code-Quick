<script lang="ts">
	import { onMount } from 'svelte';
	import { createWatchStore } from '$lib/game.svelte';
	import Timer from '$lib/components/Timer.svelte';
	import kcqLogo from '$lib/assets/images/kcq_logo.png';

	let username = $state<string | null>(null);
	let authed = $state(false);
	let durationMinutes = $state(100);
	let signupOpen = $state(false);
	let signupSaving = $state(false);
	let allowInternalClipboard = $state(true);
	let starting = $state(false);
	let exporting = $state<'finished' | 'all' | null>(null);
	let exportError = $state<string | null>(null);
	let timerFullscreen = $state(false);

	const store = createWatchStore();

	const participantCount = $derived(Object.keys(store.participants).length);
	const finishedCount = $derived(
		Object.values(store.participants).filter((p) => p.submitted_at != null).length
	);

	onMount(async () => {
		const resp = await fetch('/api/auth/me');
		if (!resp.ok) {
			window.location.replace('/');
			return;
		}
		const data = await resp.json();
		if (!data.is_admin) {
			window.location.replace('/');
			return;
		}
		username = data.discord_username;
		authed = true;

		try {
			const cfg = await fetch('/api/config');
			if (cfg.ok) signupOpen = (await cfg.json()).signup_open === true;
		} catch {
			// leave the switch showing "hidden" until a toggle succeeds
		}
	});

	async function toggleSignup() {
		signupSaving = true;
		try {
			const resp = await fetch('/api/settings', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ signup_open: !signupOpen })
			});
			if (resp.ok) signupOpen = (await resp.json()).signup_open === true;
		} catch {
			// network error; the switch keeps its last known state
		}
		signupSaving = false;
	}

	/** Pull the server's suggested filename out of Content-Disposition. */
	function filenameFrom(disposition: string | null): string | null {
		const match = disposition?.match(/filename="([^"]+)"/);
		return match ? match[1] : null;
	}

	async function exportProjects(scope: 'finished' | 'all') {
		exporting = scope;
		exportError = null;
		try {
			const resp = await fetch(`/api/game/export?scope=${scope}`);
			if (!resp.ok) {
				const body = await resp.json().catch(() => null);
				exportError = body?.error ?? 'Export failed.';
			} else {
				const blob = await resp.blob();
				const url = URL.createObjectURL(blob);
				const link = document.createElement('a');
				link.href = url;
				link.download = filenameFrom(resp.headers.get('Content-Disposition')) ?? 'kcq-projects.zip';
				document.body.appendChild(link);
				link.click();
				link.remove();
				URL.revokeObjectURL(url);
			}
		} catch {
			exportError = 'Export failed.';
		}
		exporting = null;
	}

	function handleStart() {
		starting = true;
		store.sendStartGame(durationMinutes * 60 * 1000, allowInternalClipboard);
		starting = false;
	}

	function toggleTimerFullscreen() {
		if (!document.fullscreenElement) {
			document.documentElement.requestFullscreen().catch(() => {
				// fullscreen unsupported/denied; overlay simply won't show
			});
		} else {
			document.exitFullscreen();
		}
	}

	onMount(() => {
		function onFullscreenChange() {
			timerFullscreen = document.fullscreenElement !== null;
		}
		document.addEventListener('fullscreenchange', onFullscreenChange);
		return () => document.removeEventListener('fullscreenchange', onFullscreenChange);
	});

	const labelClass = 'text-sm font-medium text-gray-300';
	const inputClass = 'w-20 rounded border border-white/20 bg-white/10 px-2 py-1 text-sm text-white';
</script>

{#if !authed}
	<div class="flex h-screen items-center justify-center bg-hacksu-grey text-gray-400">
		Checking authorization...
	</div>
{:else}
	<div class="flex min-h-screen flex-col bg-hacksu-grey text-white">
		<header class="flex items-center justify-between border-b border-gray-700/50 bg-hacksu-grey/80 px-6 py-3 backdrop-blur-sm">
			<div class="flex items-center gap-3">
				<img src={kcqLogo} alt="Kent Code Quick" class="h-8 w-auto" />
				<h1 class="text-lg font-bold">Kent Code Quick <span class="text-gray-400">Admin</span></h1>
			</div>
			<div class="flex items-center gap-4">
				<span class="text-sm text-gray-400">{username}</span>
				<a href="/watch" class="text-sm text-hacksu-blue hover:underline">Live View</a>
				<button
					type="button"
					onclick={() => fetch('/api/auth/logout', { method: 'POST' }).then(() => { window.location.href = '/'; })}
					class="text-sm text-gray-500 hover:text-white"
				>Logout</button>
			</div>
		</header>

		<main class="flex flex-1 flex-col items-center gap-8 p-8">

			{#if store.gameStatus === 'waiting' || store.gameStatus === null}
				<section class="w-full max-w-sm rounded-xl border border-white/10 bg-white/5 p-6">
					<h2 class="mb-4 text-base font-semibold">Start Game</h2>
					<div class="flex items-center gap-3">
						<label class={labelClass} for="duration">Duration (min)</label>
						<input
							id="duration"
							type="number"
							min="1"
							max="180"
							class={inputClass}
							bind:value={durationMinutes}
						/>
					</div>
					<label class="mt-3 flex items-center gap-2 text-sm text-gray-300">
						<input type="checkbox" bind:checked={allowInternalClipboard} class="h-4 w-4" />
						Allow copy/paste within a player's own editor
					</label>
					<p class="mt-2 text-sm text-gray-500">{store.lobbyCount} player{store.lobbyCount !== 1 ? 's' : ''} in lobby</p>
					{#if store.lobbyNames.length > 0}
						<ul class="mt-2 flex flex-wrap gap-1.5">
							{#each store.lobbyNames as name}
								<li class="rounded bg-white/10 px-2 py-0.5 text-xs text-gray-300">{name}</li>
							{/each}
						</ul>
					{/if}
					<button
						type="button"
						disabled={starting || store.lobbyCount === 0}
						onclick={handleStart}
						class="mt-4 w-full rounded-lg bg-hacksu-green px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-40"
					>
						{starting ? 'Starting...' : 'Start Game'}
					</button>
				</section>

			{:else if store.gameStatus === 'active'}
				<section class="w-full max-w-sm rounded-xl border border-white/10 bg-white/5 p-6">
					<h2 class="mb-2 text-base font-semibold">Game in Progress</h2>
					<div class="mb-4 flex items-center gap-3">
						<Timer elapsed={store.elapsed} durationMs={store.durationMs} />
						<button
							type="button"
							data-testid="timer-fullscreen-btn"
							onclick={toggleTimerFullscreen}
							class="rounded border border-white/20 px-2 py-1 text-xs text-gray-300 hover:bg-white/10"
						>
							Fullscreen
						</button>
					</div>
					<p class="mb-1 text-sm text-gray-400">{participantCount} participants</p>
					<p class="mb-4 text-xs text-gray-500">
						Internal copy/paste: {store.allowInternalClipboard ? 'allowed' : 'blocked'}
					</p>
					<div class="flex gap-3">
						<a href="/watch" class="flex-1 rounded-lg border border-white/20 px-4 py-2 text-center text-sm font-semibold text-white hover:bg-white/10">
							Live View
						</a>
						<button
							type="button"
							onclick={() => store.sendEndEvent()}
							class="flex-1 rounded-lg bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700"
						>
							End Game
						</button>
					</div>
				</section>

			{:else if store.gameStatus === 'ended'}
				<section class="w-full max-w-sm rounded-xl border border-white/10 bg-white/5 p-6">
					<h2 class="mb-2 text-base font-semibold">Game Ended</h2>
					<div class="flex gap-3">
						<a href="/watch" class="flex-1 rounded-lg border border-white/20 px-4 py-2 text-center text-sm font-semibold text-white hover:bg-white/10">
							View Results
						</a>
						<button
							type="button"
							onclick={() => store.sendResetGame()}
							class="flex-1 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white hover:opacity-90"
						>
							New Round
						</button>
					</div>
				</section>
			{/if}

			{#if participantCount > 0}
				<section data-testid="export-section" class="w-full max-w-sm rounded-xl border border-white/10 bg-white/5 p-6">
					<h2 class="mb-1 text-base font-semibold">Export projects</h2>
					<p class="mb-4 text-sm text-gray-400">
						{finishedCount} of {participantCount} project{participantCount !== 1 ? 's' : ''} finished.
					</p>
					<div class="flex gap-3">
						<button
							type="button"
							data-testid="export-finished"
							disabled={exporting !== null || finishedCount === 0}
							onclick={() => exportProjects('finished')}
							class="flex-1 rounded-lg bg-hacksu-green px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-40"
						>
							{exporting === 'finished' ? 'Preparing...' : `Finished (${finishedCount})`}
						</button>
						<button
							type="button"
							data-testid="export-all"
							disabled={exporting !== null}
							onclick={() => exportProjects('all')}
							class="flex-1 rounded-lg border border-white/20 px-4 py-2 text-sm font-semibold text-white hover:bg-white/10 disabled:opacity-40"
						>
							{exporting === 'all' ? 'Preparing...' : `All (${participantCount})`}
						</button>
					</div>
					{#if exportError}
						<p data-testid="export-error" class="mt-3 text-sm text-red-400">{exportError}</p>
					{/if}
					{#if store.gameStatus === 'ended'}
						<p class="mt-3 text-xs text-gray-500">
							Download before you start a new round
						</p>
					{/if}
				</section>
			{/if}

			<section class="w-full max-w-sm rounded-xl border border-white/10 bg-white/5 p-6">
				<h2 class="mb-1 text-base font-semibold">Landing page sign-up</h2>
				<p class="mb-4 text-sm text-gray-400">
					{signupOpen
						? 'Visitors see the sign-up button and can log in.'
						: 'The sign-up button is hidden.'}
				</p>
				<button
					type="button"
					data-testid="toggle-signup"
					disabled={signupSaving}
					onclick={toggleSignup}
					class="w-full rounded-lg px-4 py-2 text-sm font-semibold text-white disabled:opacity-40 {signupOpen
						? 'border border-white/20 hover:bg-white/10'
						: 'bg-hacksu-green hover:opacity-90'}"
				>
					{signupOpen ? 'Hide sign-up button' : 'Show sign-up button'}
				</button>
			</section>

		</main>
	</div>

	{#if timerFullscreen}
		<div
			data-testid="timer-fullscreen-overlay"
			class="fixed inset-0 z-50 flex flex-col items-center justify-center gap-8 bg-hacksu-grey"
		>
			<div class="text-[min(24vw,24vh)] font-bold leading-none">
				<Timer elapsed={store.elapsed} durationMs={store.durationMs} />
			</div>
			<button
				type="button"
				onclick={toggleTimerFullscreen}
				class="text-sm text-gray-400 hover:text-white"
			>
				Exit Fullscreen (Esc)
			</button>
		</div>
	{/if}
{/if}
