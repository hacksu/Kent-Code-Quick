<script lang="ts">
	const RULES = [
		'Switching to another browser tab',
		'Alt+Tab / switching to another app',
		'Minimizing the window',
		'Copying code (Ctrl+C)',
		'Cutting code (Ctrl+X)',
		'Pasting code (Ctrl+V or right-click paste)'
	];
</script>

<div class="w-full max-w-sm text-left">
	<p class="mb-3 text-center text-xs font-semibold tracking-wide text-gray-400 uppercase">
		You'll be penalized for
	</p>
	<ul class="flex flex-col gap-2">
		{#each RULES as rule (rule)}
			<li class="flex items-baseline gap-2 text-sm text-gray-300">
				<span class="text-hacksu-purple">&bull;</span>
				{rule}
			</li>
		{/each}
	</ul>
</div>
