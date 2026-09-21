"use client";

import { useEffect } from "react";
import { track, type UmamiEvent as EventName } from "@/lib/umami";

// Dispara um evento do Umami ao montar (ex.: subscribe_confirm em /lista/confirmar).
export function UmamiEvent({ name }: { name: EventName }) {
  useEffect(() => {
    track(name);
  }, [name]);
  return null;
}
