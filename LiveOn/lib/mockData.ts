import type { Testimonial } from "./types";

export const mockTestimonials: Testimonial[] = [
  {
    id: "tm-01",
    name: "David K.",
    role: "Family Historian",
    quote:
      "Seeing my posts and photos arranged into life chapters was emotional — it felt like reading the book of my own life.",
    avatar: "/media/sample-memory-3.jpg",
    rating: 5,
    highlightImages: ["/media/sample-wedding.jpg", "/media/sample-travel.jpg"],
  },
  {
    id: "tm-02",
    name: "Dawn Y.",
    role: "Memory Keeper",
    quote:
      "I had 21 years of memories on Facebook. LiveOn not only backed them up, but turned them into a story I didn’t realize I was telling all these years.",
    avatar: "/media/sample-memory-2.jpg",
    rating: 5,
    highlightImages: ["/media/sample-summer.jpg", "/media/sample-memory-4.jpg"],
  },
  {
    id: "tm-03",
    name: "Marcus L.",
    role: "Startup Founder",
    quote:
      "Our company timeline came alive. Stakeholders can relive key milestones without digging through endless posts.",
    avatar: "/media/sample-startup.jpg",
    rating: 5,
    highlightImages: ["/media/sample-memory-1.jpg", "/media/sample-summer.jpg"],
  },
];
