import localFont from "next/font/local";

// Arquivos em app/fonts/ (OFL). Ver app/fonts/README.md.
export const playfair = localFont({
  src: "./fonts/playfair-display-latin-wght-normal.woff2",
  variable: "--font-playfair",
  weight: "400 900",
  display: "swap",
  preload: true,
});

export const inter = localFont({
  src: "./fonts/inter-latin-wght-normal.woff2",
  variable: "--font-inter",
  weight: "100 900",
  display: "swap",
  preload: true,
});
