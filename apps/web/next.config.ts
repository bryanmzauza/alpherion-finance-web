import path from "node:path";
import type { NextConfig } from "next";

// O `.env` fica na raiz do monorepo; quem carrega é lib/root-env.ts (via lib/env.ts).

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.resolve(__dirname, "../.."),
  poweredByHeader: false,
  reactStrictMode: true,
};

export default nextConfig;
