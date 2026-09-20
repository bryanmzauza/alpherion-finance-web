"use client";

import Image from "next/image";
import { useState } from "react";

type Props = {
  youtubeId: string;
  title: string;
  /** Thumbnail local em public/ (sem request ao YouTube antes do clique). */
  thumbnailSrc: string;
};

// Zero cookie (§8.5): nada do YouTube carrega até o clique; depois, só youtube-nocookie.com.
export function VideoEmbed({ youtubeId, title, thumbnailSrc }: Props) {
  const [playing, setPlaying] = useState(false);

  if (playing) {
    return (
      <div className="aspect-video overflow-hidden rounded-lg border border-navy-3 bg-black">
        <iframe
          src={`https://www.youtube-nocookie.com/embed/${youtubeId}?autoplay=1&rel=0`}
          title={title}
          allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
          allowFullScreen
          referrerPolicy="strict-origin-when-cross-origin"
          className="h-full w-full"
        />
      </div>
    );
  }

  return (
    <button
      type="button"
      onClick={() => setPlaying(true)}
      aria-label={`Reproduzir: ${title} (abre o player do YouTube)`}
      className="group relative block aspect-video w-full overflow-hidden rounded-lg border border-navy-3 bg-navy-2"
    >
      <Image src={thumbnailSrc} alt="" fill sizes="(min-width: 768px) 33vw, 100vw" className="object-cover" />
      <span className="absolute inset-0 flex items-center justify-center bg-navy/40 transition-colors group-hover:bg-navy/20">
        <span className="flex h-16 w-16 items-center justify-center rounded-full bg-gold text-navy shadow-lg">
          <svg viewBox="0 0 24 24" width="28" height="28" aria-hidden="true">
            <path fill="currentColor" d="M8 5v14l11-7z" />
          </svg>
        </span>
      </span>
    </button>
  );
}
