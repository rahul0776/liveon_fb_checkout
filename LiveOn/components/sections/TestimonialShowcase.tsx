"use client";

import { useState } from "react";
import Image from "next/image";
import { ChevronLeft, ChevronRight, Star } from "lucide-react";
import type { Testimonial } from "@/lib/types";

interface Props {
  testimonials: Testimonial[];
}

export function TestimonialShowcase({ testimonials }: Props) {
  const [index, setIndex] = useState(0);
  const current = testimonials[index];

  const previous = () =>
    setIndex((prev) => (prev === 0 ? testimonials.length - 1 : prev - 1));

  const next = () => setIndex((prev) => (prev + 1) % testimonials.length);

  return (
    <section
      id="testimonials"
      className="relative mx-auto mt-6 max-w-6xl overflow-hidden rounded-[2.5rem] border border-white/10 bg-[#143150]/85 px-6 py-14 text-center sm:px-10"
    >
      <div className="pointer-events-none absolute inset-0">
        <div className="grid-glow" />
      </div>
      <div className="relative z-10 flex flex-col items-center gap-10">
        <div className="space-y-3">
          <p className="section-heading">Testimonials</p>
          <h2 className="text-3xl font-semibold text-white sm:text-4xl">
            What people are saying
          </h2>
        </div>

        <div className="grid w-full gap-6 lg:grid-cols-[220px_minmax(0,1fr)_220px] lg:items-center">
          <div className="relative hidden h-40 overflow-hidden rounded-3xl border border-white/12 bg-white/[0.08] lg:block">
            <Image
              src={current.highlightImages[0]}
              alt="Testimonial highlight"
              fill
              sizes="220px"
              className="object-cover"
            />
          </div>

          <div className="mx-auto flex max-w-2xl flex-col items-center gap-6 text-white/80">
            <div className="relative h-20 w-20 overflow-hidden rounded-full border border-white/20 shadow-ring">
              <Image
                src={current.avatar}
                alt={current.name}
                fill
                sizes="80px"
                className="object-cover"
              />
            </div>
            <div className="flex items-center justify-center gap-1 text-[#f6c35d]">
              {Array.from({ length: current.rating }).map((_, starIndex) => (
                <Star key={starIndex} className="h-5 w-5 fill-current" />
              ))}
            </div>
            <blockquote className="text-lg font-medium text-white/90 sm:text-xl">
              “{current.quote}”
            </blockquote>
            <div className="text-sm uppercase tracking-[0.32em] text-white/55">
              <span className="font-semibold text-white">{current.name}</span>
              <span className="ml-2 text-white/45">{current.role}</span>
            </div>

            <div className="flex items-center gap-4">
              <button
                type="button"
                onClick={previous}
                className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/15 bg-white/[0.06] text-white/70 transition hover:text-white"
                aria-label="Previous testimonial"
              >
                <ChevronLeft className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={next}
                className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-white/15 bg-white/[0.06] text-white/70 transition hover:text-white"
                aria-label="Next testimonial"
              >
                <ChevronRight className="h-5 w-5" />
              </button>
            </div>
          </div>

          <div className="relative hidden h-40 overflow-hidden rounded-3xl border border-white/12 bg-white/[0.08] lg:block">
            <Image
              src={current.highlightImages[1]}
              alt="Testimonial highlight"
              fill
              sizes="220px"
              className="object-cover"
            />
          </div>
        </div>

        <div className="flex gap-2">
          {testimonials.map((testimonial, dotIndex) => (
            <span
              key={testimonial.id}
              className={
                dotIndex === index
                  ? "h-2 w-6 rounded-full bg-[#f6c35d]"
                  : "h-2 w-2 rounded-full bg-white/20"
              }
            />
          ))}
        </div>
      </div>
    </section>
  );
}






