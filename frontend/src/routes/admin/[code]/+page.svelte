<script lang="ts">
	import { page } from '$app/state';
	import Editor from '$lib/components/Editor.svelte';
	import Preview from '$lib/components/Preview.svelte';
	import type { Participant } from '$lib/room.svelte';

	const roomCode = page.params.code!;
	const secret = page.url.searchParams.get('secret') ?? '';

	type RoomResult = {
		code: string;
		participants: Record<string, Participant>;
	};

	let result = $state<RoomResult | null>(null);
	let error = $state<string | null>(null);
	let selected = $state<string | null>(null);
	let activeTab = $state<'html' | 'css'>('html');

	async function load() {
		const resp = await fetch(`/api/room/${roomCode}/results?secret=${encodeURIComponent(secret)}`);
		if (resp.status === 403) { error = 'Invalid secret.'; return; }
		if (resp.status === 404) { error = 'Room not found.'; return; }
		if (!resp.ok) { error = 'Unexpected error.'; return; }
		result = await resp.json();
		const tokens = Object.keys(result!.participants);
		if (tokens.length > 0) selected = tokens[0];
	}

	load();

	function formatPenalty(ms: number): string {
		const total = Math.floor(ms / 1000);
		const m = Math.floor(total / 60);
		const s = total % 60;
		return `${m}:${String(s).padStart(2, '0')}`;
	}

	const selectedParticipant = $derived(
		selected && result ? result.participants[selected] : null
	);
</script>

{#if error}
	<div class="flex h-screen items-center justify-center text-red-600">{error}</div>
{:else if !result}
	<div class="flex h-screen items-center justify-center text-gray-400">Loading…</div>
{:else}
	<div class="flex h-screen overflow-hidden">
		<aside class="flex w-56 shrink-0 flex-col overflow-y-auto border-r border-gray-300">
			<div class="border-b border-gray-300 px-3 py-2 text-xs font-semibold uppercase text-gray-500">
				Participants
			</div>
			{#each Object.entries(result.participants) as [token, p] (token)}
				<button
					type="button"
					class={`w-full px-3 py-2 text-left hover:bg-gray-100 ${selected === token ? 'bg-gray-200 font-semibold' : ''}`}
					onclick={() => { selected = token; activeTab = 'html'; }}
				>
					<div class="truncate text-sm">{p.name}</div>
					<div class="text-xs text-gray-500">+{formatPenalty(p.penalty_ms)}</div>
				</button>
			{/each}
		</aside>

		<div class="flex flex-1 flex-col overflow-hidden">
			{#if selectedParticipant}
				<div class="flex shrink-0 items-center gap-3 border-b border-gray-300 px-4 py-2">
					<span class="font-medium">{selectedParticipant.name}</span>
					<span class="text-sm text-gray-500">Penalty: {formatPenalty(selectedParticipant.penalty_ms)}</span>
					{#if selectedParticipant.submitted_at}
						<span class="rounded bg-green-600 px-1.5 py-0.5 text-xs text-white">submitted</span>
					{/if}
				</div>

				{#if !selectedParticipant.final_html && !selectedParticipant.final_css}
					<div class="flex flex-1 items-center justify-center text-gray-400">Not submitted</div>
				{:else}
					<div class="flex shrink-0 gap-1 border-b border-gray-300 px-2 py-1">
						<button
							type="button"
							class={`cursor-pointer rounded-t border border-gray-300 px-3 py-1 ${activeTab === 'html' ? 'bg-gray-200 font-bold' : 'bg-transparent'}`}
							onclick={() => (activeTab = 'html')}
						>HTML</button>
						<button
							type="button"
							class={`cursor-pointer rounded-t border border-gray-300 px-3 py-1 ${activeTab === 'css' ? 'bg-gray-200 font-bold' : 'bg-transparent'}`}
							onclick={() => (activeTab = 'css')}
						>CSS</button>
					</div>
					<div class="grid flex-1 grid-cols-2 overflow-hidden">
						<div class="overflow-hidden border-r border-gray-300">
							<Editor
								language={activeTab}
								value={activeTab === 'html' ? (selectedParticipant.final_html ?? '') : (selectedParticipant.final_css ?? '')}
								readonly={true}
								onChange={() => {}}
							/>
						</div>
						<div class="overflow-hidden">
							<Preview
								html={selectedParticipant.final_html ?? ''}
								css={selectedParticipant.final_css ?? ''}
							/>
						</div>
					</div>
				{/if}
			{/if}
		</div>
	</div>
{/if}
