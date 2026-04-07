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
		onChange,
	}: {
		language: 'html' | 'css';
		value?: string;
		onChange: (value: string) => void;
	} = $props();

	let container: HTMLDivElement;

	onMount(() => {
		const langExtension = language === 'html' ? html() : css();

		const view = new EditorView({
			state: EditorState.create({
				doc: value,
				extensions: [
					basicSetup,
					langExtension,
					EditorView.updateListener.of((update) => {
						if (update.docChanged) {
							onChange(update.state.doc.toString());
						}
					}),
				],
			}),
			parent: container,
		});

		return () => view.destroy();
	});
</script>

<div bind:this={container} class="h-full w-full overflow-auto"></div>
