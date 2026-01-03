"use client";

import { useInView } from "@/hooks/useInView";
import clsx from "clsx";
import { ReactNode } from "react";

interface ScrollRevealProps {
    children: ReactNode;
    animation?: "fade" | "slide-up" | "slide-down" | "slide-left" | "slide-right" | "blur";
    delay?: number;
    duration?: number;
    className?: string;
}

export function ScrollReveal({
    children,
    animation = "fade",
    delay = 0,
    duration = 0.6,
    className,
}: ScrollRevealProps) {
    const { ref, isInView } = useInView({ threshold: 0.1, triggerOnce: true });

    const animations = {
        fade: "animate-fade-in",
        "slide-up": "animate-slide-up",
        "slide-down": "animate-slide-down",
        "slide-left": "animate-slide-left",
        "slide-right": "animate-slide-right",
        blur: "animate-blur-in",
    };

    return (
        <div
            ref={ref as React.RefObject<HTMLDivElement>}
            className={clsx(
                "transition-all",
                isInView ? animations[animation] : "translate-y-8",
                className
            )}
            style={{
                animationDelay: `${delay}ms`,
                animationDuration: `${duration}s`,
                animationFillMode: "both",
            }}
        >
            {children}
        </div>
    );
}
