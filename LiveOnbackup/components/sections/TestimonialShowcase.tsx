"use client";

import { Marquee } from "@/components/animations/Marquee";
import Image from "next/image";
import { Star } from "lucide-react";
import type { Testimonial } from "@/lib/types";

interface Props {
  testimonials: Testimonial[];
}

export function TestimonialShowcase({ testimonials }: Props) {
  return (
    <section id="testimonials" className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-0">
      <div className="space-y-6 text-center">
        <p className="section-heading">Testimonials</p>
        <h2 className="text-3xl font-semibold text-white sm:text-4xl">
          What people are saying
        </h2>
      </div>

      <Marquee speed={50} className="mt-10">
        {testimonials.map((testimonial) => (
          <div
            key={testimonial.id}
            className="glass-panel navy-fade-border relative w-[400px] overflow-hidden p-6 text-left"
          >
            <div className="grid-glow" />
            <div className="relative z-10 space-y-4">
              <div className="flex items-center gap-4">
                <div className="relative h-14 w-14 overflow-hidden rounded-full border border-white/20">
                  <Image
                    src={testimonial.avatar}
                    alt={testimonial.name}
                    fill
                    sizes="56px"
                    className="object-cover"
                  />
                </div>
                <div>
                  <p className="font-semibold text-white">{testimonial.name}</p>
                  <p className="text-xs text-white/60">{testimonial.role}</p>
                </div>
              </div>

              <div className="flex items-center gap-1 text-[#f6c35d]">
                {Array.from({ length: testimonial.rating }).map((_, starIndex) => (
                  <Star key={starIndex} className="h-4 w-4 fill-current" />
                ))}
              </div>

              <blockquote className="text-sm text-white/80">
                "{testimonial.quote}"
              </blockquote>
            </div>
          </div>
        ))}
      </Marquee>
    </section>
  );
}








