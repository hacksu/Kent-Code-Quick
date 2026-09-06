<script lang="ts">
	import discordIcon from '$lib/assets/images/logos/discord.svg';
	import instagramIcon from '$lib/assets/images/logos/instagram.svg';
	import githubIcon from '$lib/assets/images/logos/github.svg';

	const socialLinks = [
		{ name: 'Instagram', href: 'https://www.instagram.com/hacksu/', icon: instagramIcon },
		{ name: 'GitHub', href: 'https://github.com/hacksu', icon: githubIcon },
		{ name: 'Discord', href: 'https://discord.gg/hrRfNQBz5z', icon: discordIcon }
	];
</script>

<footer class="w-full bg-hacksu-grey py-8 px-4">
	<div class="mx-auto flex max-w-7xl items-center justify-center gap-6">
		{#each socialLinks as link (link.name)}
			<a
				href={link.href}
				target="_blank"
				rel="noopener noreferrer"
				class="text-white transition-colors duration-200 hover:text-hacksu-green"
				aria-label={link.name}
			>
				<img src={link.icon} alt={link.name} class="icon-white h-8 w-8" />
			</a>
		{/each}
	</div>
</footer>

<style>
	.icon-white {
		filter: brightness(0) invert(1);
	}
</style>
