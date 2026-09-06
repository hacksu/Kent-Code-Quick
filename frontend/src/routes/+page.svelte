<script lang="ts">
	import { onMount } from 'svelte';
	import kcqLogo from '$lib/assets/images/kcq_logo.png';
	import discordIcon from '$lib/assets/images/logos/discord.svg';
	import ParticleBackground from '$lib/components/ParticleBackground.svelte';
	import Footer from '$lib/components/Footer.svelte';
	import { DISCORD_INVITE } from '$lib/links';

	const EVENT_DATE = 'September 24th';
	const EVENT_TIME = '6:00-9:00pm';
	const EVENT_PLACE = 'Math Emporium, KSU Library room 210H';

	let checking = $state(true);
	let clientId = $state('');
	let configError = $state(false);
	let signupOpen = $state(false);

	onMount(async () => {
		try {
			const resp = await fetch('/api/auth/me');
			if (resp.ok) {
				const data = await resp.json();
				window.location.replace(data.is_admin ? '/admin' : '/lobby');
				return;
			}
		} catch {
			// network error, fall through
		}

		// The OAuth client id comes from the server so it can never drift from
		// the client secret the server exchanges the code with.
		try {
			const cfg = await fetch('/api/config');
			if (cfg.ok) {
				const data = await cfg.json();
				clientId = data.discord_client_id ?? '';
				signupOpen = data.signup_open === true;
			}
		} catch {
			// leave clientId empty; the button below explains the problem
		}
		configError = clientId === '';
		checking = false;
	});

	// crypto.randomUUID is only defined in secure contexts, and the event is
	// often served over plain HTTP on a local network -- fall back to
	// getRandomValues, which is not gated, and then to Math.random.
	function randomState(): string {
		if (typeof crypto !== 'undefined') {
			if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
			if (typeof crypto.getRandomValues === 'function') {
				const bytes = crypto.getRandomValues(new Uint8Array(16));
				return Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
			}
		}
		return `${Date.now().toString(16)}${Math.random().toString(16).slice(2)}`;
	}

	function login() {
		if (!clientId) return;
		const redirectUri = `${window.location.origin}/auth/callback`;
		// CSRF protection: the callback only exchanges a code that comes back
		// with the state value we generated for this browser.
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

	const specLabel = 'font-display text-[0.7rem] font-semibold tracking-[0.16em] text-gray-500 uppercase';
	const specCell = 'grid justify-items-center gap-0.5 px-4 py-3.5';
	const ctaClass =
		'mt-1 flex cursor-pointer items-center gap-2.5 rounded-lg bg-hacksu-green px-5 py-3.5 text-[0.95rem] font-medium text-[#07130d] no-underline transition-colors hover:bg-hacksu-green/90 disabled:cursor-not-allowed disabled:opacity-40';
	const noteClass = 'font-display text-sm tracking-[0.1em] text-gray-500 uppercase';
</script>

<ParticleBackground />

{#if checking}
	<div class="relative z-10 flex min-h-screen items-center justify-center">
		<div
			class="h-6 w-6 animate-spin rounded-full border-2 border-white/20 border-t-hacksu-green"
		></div>
	</div>
{:else}
	<div class="relative z-10 flex min-h-screen flex-col font-body">
		<main
			class="flex flex-1 flex-col items-center justify-center gap-[clamp(0.85rem,2.2vh,1.35rem)] px-5 py-[clamp(1.5rem,5vh,3.5rem)] text-center text-white"
		>
			<img class="w-[clamp(88px,15vw,126px)]" src={kcqLogo} alt="" />

			<h1
				class="font-display text-[clamp(2.6rem,8vw,4.6rem)] leading-[0.9] font-extrabold tracking-[0.01em] uppercase"
			>
				Kent Code Quick
			</h1>

			<p class="max-w-[46ch] text-[clamp(1rem,1.5vw,1.1rem)] text-gray-400">
				A live front-end sprint. You get a design and a hundred minutes to rebuild it from
				scratch and make it yours.
			</p>

			<dl
				class="grid w-full max-w-[620px] grid-cols-1 overflow-hidden rounded-xl border border-white/10 bg-hacksu-grey/70 backdrop-blur-sm sm:grid-cols-3"
			>
				<div class={specCell}>
					<dt class={specLabel}>On the clock</dt>
					<dd
						class="font-display text-xl font-semibold tracking-wide text-hacksu-blue tabular-nums"
					>
						100:00
					</dd>
				</div>
				<div class="{specCell} border-t border-white/10 sm:border-t-0 sm:border-l">
					<dt class={specLabel}>You write</dt>
					<dd class="text-[0.92rem]">HTML &middot; CSS &middot; JS</dd>
				</div>
				<div class="{specCell} border-t border-white/10 sm:border-t-0 sm:border-l">
					<dt class={specLabel}>You can't</dt>
					<dd class="text-[0.92rem]">Use AI, paste, or tab out</dd>
				</div>
			</dl>

			<div class="grid gap-1">
				<p
					class="flex flex-wrap items-baseline justify-center gap-x-3 gap-y-1 font-racing text-[clamp(1.3rem,3vw,1.75rem)] tracking-wide"
				>
					{EVENT_DATE}
					<span class="text-hacksu-green tabular-nums">{EVENT_TIME}</span>
				</p>
				<p class="text-sm text-gray-400">{EVENT_PLACE}</p>
			</div>

			{#if signupOpen}
				<button type="button" onclick={login} disabled={configError} class={ctaClass}>
					<img src={discordIcon} alt="" class="h-5 w-5" />
					Sign up with Discord
				</button>
			{:else}
				<a
					href={DISCORD_INVITE}
					target="_blank"
					rel="noopener noreferrer"
					class={ctaClass}
					data-testid="discord-cta"
				>
					<img src={discordIcon} alt="" class="h-5 w-5" />
					Join the Discord for more updates
				</a>
			{/if}

			{#if signupOpen && configError}
				<p class="text-sm text-red-400" data-testid="config-error">
					Sign-up is unavailable: the server has no Discord client ID configured.
				</p>
			{:else}
				<p class={noteClass}>No experience required &middot; Bring a laptop</p>
			{/if}
		</main>

		<Footer />
	</div>
{/if}
