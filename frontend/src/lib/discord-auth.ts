export function randomState(): string {
	if (typeof crypto !== 'undefined') {
		if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
		if (typeof crypto.getRandomValues === 'function') {
			const bytes = crypto.getRandomValues(new Uint8Array(16));
			return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
		}
	}
	return `${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`;
}

export function startDiscordLogin(clientId: string): void {
	if (!clientId) return;
	const redirectUri = `${window.location.origin}/auth/callback`;
	const state = randomState();
	sessionStorage.setItem('oauthState', state);
	const params = new URLSearchParams({
		client_id: clientId,
		redirect_uri: redirectUri,
		response_type: 'code',
		scope: 'identify guilds.members.read',
		state
	});
	window.location.href = `https://discord.com/oauth2/authorize?${params}`;
}
