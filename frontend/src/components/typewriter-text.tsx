"use client";

import { useEffect, useState } from "react";

import { cn } from "@/lib/utils";

export function TypewriterText({
  text,
  speed = 45,
  startDelay = 300,
  className,
}: {
  text: string;
  speed?: number;
  startDelay?: number;
  className?: string;
}) {
  const [count, setCount] = useState(0);

  useEffect(() => {
    setCount(0);
    let i = 0;
    let interval: ReturnType<typeof setInterval> | undefined;
    const timeout = setTimeout(() => {
      interval = setInterval(() => {
        i += 1;
        setCount(i);
        if (i >= text.length && interval) clearInterval(interval);
      }, speed);
    }, startDelay);
    return () => {
      clearTimeout(timeout);
      if (interval) clearInterval(interval);
    };
  }, [text, speed, startDelay]);

  const done = count >= text.length;

  return (
    <span className={className}>
      <span aria-hidden>
        {text.slice(0, count)}
        <span
          className={cn(
            "ml-0.5 inline-block h-[0.9em] w-[3px] translate-y-[3px] bg-current align-middle",
            done ? "animate-pulse" : "opacity-90",
          )}
        />
      </span>
      <span className="sr-only">{text}</span>
    </span>
  );
}
