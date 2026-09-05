<script lang="ts">
	import favicon from '$lib/assets/images/favicon.png';
	import '../app.css';

	let { children } = $props();
</script>

<svelte:head>
	<link rel="icon" type="image/png" href={favicon} />
	<title>Kent Code Quick</title>
	<meta
		name="description"
		content="Kent Code Quick - HacKSU's live front-end coding competition. Race the clock, build, and ship."
	/>

	<!-- Open Graph -->
	<meta property="og:type" content="website" />
	<meta property="og:site_name" content="HacKSU" />
	<meta property="og:title" content="Kent Code Quick" />
	<meta
		property="og:description"
		content="HacKSU's live front-end coding competition. Race the clock, build, and ship."
	/>
</svelte:head>

{@render children()}
