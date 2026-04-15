<div class="splash">
	<h1 class="wordmark">drift</h1>
	<p class="waiting">Looking for an opponent</p>
	<div class="dots"><span></span><span></span><span></span></div>
</div>

<style>
	.splash {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		height: 100vh;
		gap: 20px;
	}
	.wordmark {
		font-size: clamp(56px, 12vw, 90px);
		font-weight: 700;
		letter-spacing: -0.05em;
		color: #f4ecdf;
	}
	.waiting {
		color: #b5a992;
	}
	.dots {
		display: flex;
		gap: 6px;
	}
	.dots span {
		width: 7px;
		height: 7px;
		border-radius: 50%;
		background: #6b624f;
		animation: pulse 1.2s ease-in-out infinite;
	}
	.dots span:nth-child(2) {
		animation-delay: 0.2s;
	}
	.dots span:nth-child(3) {
		animation-delay: 0.4s;
	}
	@keyframes pulse {
		0%,
		80%,
		100% {
			opacity: 0.35;
		}
		40% {
			opacity: 1;
		}
	}
</style>
