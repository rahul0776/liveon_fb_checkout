"use client";

import { useMousePosition } from "@/hooks/useMousePosition";
import { ReactNode, useRef } from "react";

interface FlashlightCardProps {
    children: ReactNode;
    className?: string;
    intensity?: number;
}

export function FlashlightCard({ children, className, intensity = 0.3 }: FlashlightCardProps) {
    const cardRef = useRef<HTMLDivElement>(null);
    const { mousePosition, isHovering } = useMousePosition(cardRef);

    return (
        <div ref={cardRef} className={className} style={{ position: "relative" }}>
            {/* Flashlight effect on background */}
            {isHovering && (
                <div
                    className="absolute inset-0 pointer-events-none rounded-[inherit] transition-opacity duration-300"
                    style={{
                        background: `radial-gradient(600px circle at ${mousePosition.x}px ${mousePosition.y}px, rgba(246, 195, 93, ${intensity}), transparent 40%)`,
                        opacity: isHovering ? 1 : 0,
                    }}
                />
            )}

            {/* Flashlight effect on border */}
            {isHovering && (
                <div
                    className="absolute inset-0 pointer-events-none rounded-[inherit] transition-opacity duration-300"
                    style={{
                        background: `radial-gradient(400px circle at ${mousePosition.x}px ${mousePosition.y}px, rgba(246, 195, 93, 0.6), transparent 40%)`,
                        opacity: isHovering ? 1 : 0,
                        maskImage: "linear-gradient(black, black) content-box, linear-gradient(black, black)",
                        maskComposite: "exclude",
                        WebkitMaskComposite: "xor",
                        padding: "1px",
                    }}
                />
            )}

            {children}
        </div>
    );
}
