import path from "node:path";
import createMDX from "@next/mdx";
import type { NextConfig } from "next";

// O `.env` fica na raiz do monorepo; quem carrega é lib/root-env.ts (via lib/env.ts).

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.resolve(__dirname, "../.."),
  poweredByHeader: false,
  reactStrictMode: true,
  pageExtensions: ["ts", "tsx", "mdx"],
  images: {
    formats: ["image/avif", "image/webp"],
  },
};

// Textos legais em MDX com frontmatter (version, date) exportado como `frontmatter`.
// Plugins como string: exigência do Turbopack.
const withMDX = createMDX({
  options: {
    remarkPlugins: [["remark-gfm"], ["remark-frontmatter"], ["remark-mdx-frontmatter", { name: "frontmatter" }]],
  },
});

export default withMDX(nextConfig);
