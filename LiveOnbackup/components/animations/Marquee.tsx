"use client";

import clsx from "clsx";
import { ReactNode } from "react";

interface MarqueeProps {
    children: ReactNode;
    speed?: number;
    direction?: "left" | "right";
    className?: string;
}

export function Marquee({ children, speed = 40, direction = "left", className }: MarqueeProps) {
    return (
        <div className={clsx("relative overflow-hidden", className)}>
            {/* Alpha mask fade edges */}
            <div className="absolute inset-y-0 left-0 w-32 bg-gradient-to-r from-[#0f253d] to-transparent z-10 pointer-events-none" />
            <div className="absolute inset-y-0 right-0 w-32 bg-gradient-to-l from-[#0f253d] to-transparent z-10 pointer-events-none" />

            <div
                className="flex gap-8"
                style={{
                    animation: `marquee-${direction} ${speed}s linear infinite`,
                }}
            >
                {/* Duplicate children for seamless loop */}
                <div className="flex gap-8 shrink-0">{children}</div>
                <div className="flex gap-8 shrink-0">{children}</div>
            </div>
        </div>
    );
}
