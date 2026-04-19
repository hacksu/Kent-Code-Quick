<script lang="ts">
	import { goto } from '$app/navigation';

	let roomCode = $state('');
	let name = $state('');
	let role = $state<'participant' | 'presenter' | 'admin'>('participant');
	let secret = $state('');

	const valid = $derived(
		roomCode.trim().length > 0 &&
		name.trim().length > 0 &&
		(role !== 'admin' || secret.trim().length > 0)
	);

	function handleSubmit() {
		if (!valid) return;
		const code = roomCode.trim().toUpperCase();
		if (role === 'participant') {
			goto(`/room/${code}?name=${encodeURIComponent(name.trim())}`);
		} else if (role === 'presenter') {
			goto(`/presenter/${code}`);
		} else {
			goto(`/admin/${code}?secret=${encodeURIComponent(secret.trim())}`);
		}
	}

	const inputClass = 'w-full rounded-lg border border-white/20 bg-white/10 px-3 py-2 text-sm text-white placeholder-gray-500 focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20';
	const labelClass = 'mb-1 block text-sm font-medium text-gray-300';
</script>

<div class="flex min-h-screen items-center justify-center bg-hacksu-grey p-4">
	<div class="w-full max-w-sm">
		<div class="mb-8 text-center">
			<h1 class="text-2xl font-bold text-white">Kent Code Quick</h1>
		</div>

		<div class="rounded-xl border border-white/10 bg-white/5 p-8 shadow-sm">
			<form class="space-y-4" onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
				<div>
					<label class={labelClass} for="room-code">Room code</label>
					<input
						id="room-code"
						type="text"
						class={inputClass}
						placeholder="ABCD"
						bind:value={roomCode}
						required
					/>
				</div>

				<div>
					<label class={labelClass} for="name">Name</label>
					<input
						id="name"
						type="text"
						class={inputClass}
						placeholder="Your name"
						bind:value={name}
						required
					/>
				</div>

				<div>
					<label class={labelClass} for="role">Role</label>
					<select
						id="role"
						class={inputClass}
						bind:value={role}
					>
						<option value="participant">Participant</option>
						<option value="presenter">Presenter</option>
						<option value="admin">Admin</option>
					</select>
				</div>

				{#if role === 'admin'}
					<div>
						<label class={labelClass} for="secret">Secret</label>
						<input
							id="secret"
							type="password"
							class={inputClass}
							placeholder="Admin secret"
							bind:value={secret}
							required
						/>
					</div>
				{/if}

				<button
					type="submit"
					disabled={!valid}
					class="mt-2 w-full rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-dark disabled:cursor-not-allowed disabled:opacity-40"
				>
					Join Room
				</button>
			</form>
		</div>
	</div>
</div>
