"use client";

import { useInView } from "@/hooks/useInView";
import { useEffect, useState } from "react";

interface TextRevealProps {
    text: string;
    className?: string;
    delay?: number;
    staggerDelay?: number;
}

export function TextReveal({ text, className, delay = 0, staggerDelay = 50 }: TextRevealProps) {
    const { ref, isInView } = useInView({ threshold: 0.1, triggerOnce: true });
    const [revealedChars, setRevealedChars] = useState(0);

    useEffect(() => {
        if (!isInView) return;

        const timeout = setTimeout(() => {
            const interval = setInterval(() => {
                setRevealedChars((prev) => {
                    if (prev >= text.length) {
                        clearInterval(interval);
                        return prev;
                    }
                    return prev + 1;
                });
            }, staggerDelay);

            return () => clearInterval(interval);
        }, delay);

        return () => clearTimeout(timeout);
    }, [isInView, text.length, delay, staggerDelay]);

    // Split text into words to keep them together
    const words = text.split(" ");
    let charIndex = 0;

    return (
        <span ref={ref as React.RefObject<HTMLSpanElement>} className={className}>
            {words.map((word, wIndex) => {
                const wordContent = (
                    <span key={wIndex} className="inline-block whitespace-nowrap">
                        {word.split("").map((char, cIndex) => {
                            const currentGlobalIndex = charIndex + cIndex;
                            return (
                                <span
                                    key={cIndex}
                                    className="inline-block"
                                    style={{
                                        clipPath: currentGlobalIndex < revealedChars ? "inset(0 0 0 0)" : "inset(0 0 100% 0)",
                                        transition: "clip-path 0.3s ease-out",
                                    }}
                                >
                                    {char}
                                </span>
                            );
                        })}
                    </span>
                );

                // Increment char index by word length + 1 for the space
                charIndex += word.length + 1;

                return (
                    <span key={wIndex}>
                        {wordContent}
                        {wIndex < words.length - 1 && (
                            <span className="inline-block">
                                &nbsp;
                            </span>
                        )}
                    </span>
                );
            })}
        </span>
    );
}
