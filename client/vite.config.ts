import { sveltekit } from "@sveltejs/kit/vite";
import { defineConfig } from "vite";

export default defineConfig({
	plugins: [sveltekit()],
	server: {
		host: "0.0.0.0",
		port: 5173,
		hmr: {
			// Inside Docker the HMR websocket must reach the browser via the host-mapped port
			clientPort: 5173,
		},
	},
});
