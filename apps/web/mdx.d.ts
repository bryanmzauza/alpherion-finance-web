declare module "*.mdx" {
  import type { MDXProps } from "mdx/types";
  import type { JSX } from "react";

  /** Frontmatter exportado por remark-mdx-frontmatter (next.config.ts). */
  export const frontmatter: { title: string; version: string; date: string };
  export default function MDXContent(props: MDXProps): JSX.Element;
}
