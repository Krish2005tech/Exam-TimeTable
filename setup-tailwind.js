import { execSync } from "child_process";
import fs from "fs";

const run = (cmd) => execSync(cmd, { stdio: "inherit" });

console.log("Installing Tailwind dependencies...");
run("npm install -D tailwindcss postcss autoprefixer @tailwindcss/postcss");

console.log("Initializing Tailwind...");
run("npx tailwindcss init -p");

console.log("Writing src/index.css...");
fs.writeFileSync("src/index.css", '@import "tailwindcss";\n');

console.log("Writing tailwind.config.js...");
fs.writeFileSync(
  "tailwind.config.js",
`/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx,vue,svelte}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
`
);

console.log("Writing postcss.config.js...");
fs.writeFileSync(
  "postcss.config.js",
`export default {
  plugins: {
    "@tailwindcss/postcss": {},
    autoprefixer: {},
  },
}
`
);

console.log("✅ Tailwind setup complete!");
