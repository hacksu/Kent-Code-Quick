<script lang="ts">
	import { onMount } from 'svelte';
	import { basicSetup } from 'codemirror';
	import { EditorView } from '@codemirror/view';
	import { EditorState } from '@codemirror/state';
	import { html } from '@codemirror/lang-html';
	import { css } from '@codemirror/lang-css';

	let {
		language,
		value = '',
		readonly = false,
		onChange,
	}: {
		language: 'html' | 'css';
		value?: string;
		readonly?: boolean;
		onChange: (value: string) => void;
	} = $props();

	let container: HTMLDivElement;

	onMount(() => {
		let debounceTimer: ReturnType<typeof setTimeout> | null = null;

		const langExtension = language === 'html' ? html() : css();

		const extensions = [
			basicSetup,
			langExtension,
			EditorState.readOnly.of(readonly),
			EditorView.updateListener.of((update) => {
				if (update.docChanged) {
					if (debounceTimer !== null) clearTimeout(debounceTimer);
					debounceTimer = setTimeout(() => {
						onChange(update.state.doc.toString());
					}, 300);
				}
			}),
		];

		const view = new EditorView({
			state: EditorState.create({ doc: value, extensions }),
			parent: container,
		});

		return () => {
			if (debounceTimer !== null) clearTimeout(debounceTimer);
			view.destroy();
		};
	});
</script>

<div bind:this={container} class="h-full w-full overflow-auto"></div>
