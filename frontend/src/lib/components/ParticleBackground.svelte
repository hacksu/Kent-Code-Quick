<script lang="ts">
	import { onMount, onDestroy } from 'svelte';

	// HacKSU's signature particle-network backdrop. Sits behind page content
	// on the dark hacksu-grey background.
	let canvas: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D | null = null;
	let animationFrame = 0;
	let particles: Array<{ x: number; y: number; vx: number; vy: number }> = [];
	const particleCount = 90;
	const connectionDistance = 150;

	function initParticles() {
		if (typeof window === 'undefined' || !canvas) return;
		ctx = canvas.getContext('2d');
		if (!ctx) return;

		canvas.width = window.innerWidth;
		canvas.height = window.innerHeight;

		particles = Array.from({ length: particleCount }, () => ({
			x: Math.random() * canvas.width,
			y: Math.random() * canvas.height,
			vx: (Math.random() - 0.5) * 0.5,
			vy: (Math.random() - 0.5) * 0.5
		}));

		animate();
	}

	function animate() {
		if (!ctx || !canvas) return;

		ctx.clearRect(0, 0, canvas.width, canvas.height);
		ctx.lineWidth = 1;

		for (let i = 0; i < particles.length; i++) {
			const p = particles[i];

			p.x += p.vx;
			p.y += p.vy;

			if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
			if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

			p.x = Math.max(0, Math.min(canvas.width, p.x));
			p.y = Math.max(0, Math.min(canvas.height, p.y));

			for (let j = i + 1; j < particles.length; j++) {
				const p2 = particles[j];
				const dx = p.x - p2.x;
				const dy = p.y - p2.y;
				const distance = Math.sqrt(dx * dx + dy * dy);

				if (distance < connectionDistance) {
					const opacity = (1 - distance / connectionDistance) * 0.95;
					ctx.strokeStyle = `rgba(53, 201, 130, ${opacity})`;
					ctx.beginPath();
					ctx.moveTo(p.x, p.y);
					ctx.lineTo(p2.x, p2.y);
					ctx.stroke();
				}
			}

			ctx.fillStyle = 'rgba(53, 201, 130, 0.9)';
			ctx.beginPath();
			ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
			ctx.fill();
		}

		animationFrame = requestAnimationFrame(animate);
	}

	function handleResize() {
		if (typeof window === 'undefined' || !canvas) return;
		canvas.width = window.innerWidth;
		canvas.height = window.innerHeight;
	}

	onMount(() => {
		if (typeof window === 'undefined') return;
		initParticles();
		window.addEventListener('resize', handleResize);
	});

	onDestroy(() => {
		if (typeof window === 'undefined') return;
		if (animationFrame) cancelAnimationFrame(animationFrame);
		window.removeEventListener('resize', handleResize);
	});
</script>

<div class="pointer-events-none fixed inset-0 z-0 bg-hacksu-grey"></div>
<canvas bind:this={canvas} class="pointer-events-none fixed inset-0 z-0 h-full w-full"></canvas>
