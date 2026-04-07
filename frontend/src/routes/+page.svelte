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
		const code = roomCode.trim();
		if (role === 'participant') {
			goto(`/room/${code}?name=${encodeURIComponent(name.trim())}`);
		} else if (role === 'presenter') {
			goto(`/presenter/${code}`);
		} else {
			goto(`/admin/${code}?secret=${encodeURIComponent(secret.trim())}`);
		}
	}
</script>

<form onsubmit={(e) => { e.preventDefault(); handleSubmit(); }}>
	<label>
		Room code
		<input type="text" bind:value={roomCode} required />
	</label>

	<label>
		Name
		<input type="text" bind:value={name} required />
	</label>

	<label>
		Role
		<select bind:value={role}>
			<option value="participant">Participant</option>
			<option value="presenter">Presenter</option>
			<option value="admin">Admin</option>
		</select>
	</label>

	{#if role === 'admin'}
		<label>
			Secret
			<input type="password" bind:value={secret} required />
		</label>
	{/if}

	<button type="submit" disabled={!valid}>Join</button>
</form>
