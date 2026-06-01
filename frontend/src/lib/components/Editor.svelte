<script lang="ts">
	import { onMount } from 'svelte';
	import { basicSetup } from 'codemirror';
	import { EditorView, keymap } from '@codemirror/view';
	import { Compartment, EditorState } from '@codemirror/state';
	import { indentWithTab } from '@codemirror/commands';
	import { html } from '@codemirror/lang-html';
	import { css } from '@codemirror/lang-css';
	import { javascript } from '@codemirror/lang-javascript';
	import { oneDark } from '@codemirror/theme-one-dark';

	let {
		language,
		value = '',
		readonly = false,
		blockCopyPaste = true,
		onChange,
		onCopyAttempt,
	}: {
		language: 'html' | 'css' | 'js';
		value?: string;
		readonly?: boolean;
		blockCopyPaste?: boolean;
		onChange: (value: string) => void;
		onCopyAttempt?: () => void;
	} = $props();

	let container: HTMLDivElement;

	const noPasteCopyExtension = EditorView.domEventHandlers({
		paste: (e) => { if (!blockCopyPaste) return false; e.preventDefault(); onCopyAttempt?.(); return true; },
		copy:  (e) => { if (!blockCopyPaste) return false; e.preventDefault(); onCopyAttempt?.(); return true; },
		cut:   (e) => { if (!blockCopyPaste) return false; e.preventDefault(); onCopyAttempt?.(); return true; },
	});

	const readOnlyCompartment = new Compartment();
	const langCompartment = new Compartment();

	onMount(() => {
		let debounceTimer: ReturnType<typeof setTimeout> | null = null;
		let lastReportedValue = value;

		const view = new EditorView({
			state: EditorState.create({
				doc: value,
				extensions: [
					basicSetup,
					oneDark,
					keymap.of([indentWithTab]),
					langCompartment.of(language === 'html' ? html() : language === 'css' ? css() : javascript()),
					noPasteCopyExtension,
					readOnlyCompartment.of(EditorState.readOnly.of(readonly)),
					EditorView.updateListener.of((update) => {
						if (update.docChanged) {
							const v = update.state.doc.toString();
							lastReportedValue = v;
							if (debounceTimer !== null) clearTimeout(debounceTimer);
							debounceTimer = setTimeout(() => { debounceTimer = null; onChange(v); }, 300);
						}
					}),
				],
			}),
			parent: container,
		});

		const block = (e: Event) => { e.preventDefault(); onCopyAttempt?.(); };
		if (blockCopyPaste) {
			document.addEventListener('paste', block, true);
			document.addEventListener('copy',  block, true);
		}

		$effect(() => {
			view.dispatch({ effects: readOnlyCompartment.reconfigure(EditorState.readOnly.of(readonly)) });
		});

		$effect(() => {
			const langExt = language === 'html' ? html() : language === 'css' ? css() : javascript();
			view.dispatch({ effects: langCompartment.reconfigure(langExt) });
		});

		// Sync external value changes (tab switch) without triggering onChange.
		// Flush any pending debounce first so unsaved typed content isn't lost.
		$effect(() => {
			if (value !== lastReportedValue) {
				if (debounceTimer !== null) {
					clearTimeout(debounceTimer);
					debounceTimer = null;
					const unsaved = view.state.doc.toString();
					if (unsaved !== value) onChange(unsaved);
				}
				lastReportedValue = value;
				view.dispatch({
					changes: { from: 0, to: view.state.doc.length, insert: value },
				});
			}
		});

		return () => {
			if (debounceTimer !== null) clearTimeout(debounceTimer);
			if (blockCopyPaste) {
				document.removeEventListener('paste', block, true);
				document.removeEventListener('copy',  block, true);
			}
			view.destroy();
		};
	});
</script>

<div bind:this={container} class="h-full w-full overflow-auto"></div>
