"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { ReactNode, useEffect, useState } from "react";
import clsx from "clsx";

interface CardCarouselProps {
    cards: ReactNode[];
    autoRotateInterval?: number;
    className?: string;
}

export function CardCarousel({ cards, autoRotateInterval = 5000, className }: CardCarouselProps) {
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isAutoRotating, setIsAutoRotating] = useState(true);

    const goToNext = () => {
        setCurrentIndex((prev) => (prev + 1) % cards.length);
        setIsAutoRotating(false);
    };

    const goToPrev = () => {
        setCurrentIndex((prev) => (prev - 1 + cards.length) % cards.length);
        setIsAutoRotating(false);
    };

    useEffect(() => {
        if (!isAutoRotating) return;

        const interval = setInterval(() => {
            setCurrentIndex((prev) => (prev + 1) % cards.length);
        }, autoRotateInterval);

        return () => clearInterval(interval);
    }, [isAutoRotating, autoRotateInterval, cards.length]);

    return (
        <div className={clsx("relative", className)}>
            <div className="overflow-hidden">
                <div
                    className="flex transition-transform duration-700 ease-out"
                    style={{ transform: `translateX(-${currentIndex * 100}%)` }}
                >
                    {cards.map((card, index) => (
                        <div key={index} className="w-full shrink-0">
                            {card}
                        </div>
                    ))}
                </div>
            </div>

            {/* Navigation arrows */}
            <button
                onClick={goToPrev}
                className="absolute left-4 top-1/2 -translate-y-1/2 z-20 flex h-10 w-10 items-center justify-center rounded-full border border-white/20 bg-white/10 backdrop-blur-sm text-white/80 transition hover:bg-white/20 hover:text-white"
                aria-label="Previous card"
            >
                <ChevronLeft className="h-5 w-5" />
            </button>
            <button
                onClick={goToNext}
                className="absolute right-4 top-1/2 -translate-y-1/2 z-20 flex h-10 w-10 items-center justify-center rounded-full border border-white/20 bg-white/10 backdrop-blur-sm text-white/80 transition hover:bg-white/20 hover:text-white"
                aria-label="Next card"
            >
                <ChevronRight className="h-5 w-5" />
            </button>

            {/* Indicators */}
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-20 flex gap-2">
                {cards.map((_, index) => (
                    <button
                        key={index}
                        onClick={() => {
                            setCurrentIndex(index);
                            setIsAutoRotating(false);
                        }}
                        className={clsx(
                            "h-2 rounded-full transition-all",
                            index === currentIndex ? "w-8 bg-[#f6c35d]" : "w-2 bg-white/30"
                        )}
                        aria-label={`Go to card ${index + 1}`}
                    />
                ))}
            </div>
        </div>
    );
}
