"use client";

import { useEffect, useState } from "react";

interface MousePosition {
    x: number;
    y: number;
}

export function useMousePosition(elementRef: React.RefObject<HTMLElement>) {
    const [mousePosition, setMousePosition] = useState<MousePosition>({ x: 0, y: 0 });
    const [isHovering, setIsHovering] = useState(false);

    useEffect(() => {
        const element = elementRef.current;
        if (!element) return;

        const handleMouseMove = (e: MouseEvent) => {
            const rect = element.getBoundingClientRect();
            setMousePosition({
                x: e.clientX - rect.left,
                y: e.clientY - rect.top,
            });
        };

        const handleMouseEnter = () => setIsHovering(true);
        const handleMouseLeave = () => setIsHovering(false);

        element.addEventListener("mousemove", handleMouseMove);
        element.addEventListener("mouseenter", handleMouseEnter);
        element.addEventListener("mouseleave", handleMouseLeave);

        return () => {
            element.removeEventListener("mousemove", handleMouseMove);
            element.removeEventListener("mouseenter", handleMouseEnter);
            element.removeEventListener("mouseleave", handleMouseLeave);
        };
    }, [elementRef]);

    return { mousePosition, isHovering };
}
