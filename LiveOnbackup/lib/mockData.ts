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
      "I had 21 years of memories on Facebook. LiveOn not only backed them up, but turned them into a story I didn't realize I was telling all these years.",
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

export const mockLogos = [
  { name: "TechCorp", src: "/media/logo-1.svg" },
  { name: "DataFlow", src: "/media/logo-2.svg" },
  { name: "CloudSync", src: "/media/logo-3.svg" },
  { name: "MemoryVault", src: "/media/logo-4.svg" },
  { name: "SocialArchive", src: "/media/logo-5.svg" },
  { name: "TimeKeeper", src: "/media/logo-6.svg" },
];

export const mockFeatureCards = [
  {
    id: "feature-1",
    title: "Timeline Explorer",
    description: "Navigate your memories chronologically with our interactive timeline. Filter by year, event type, or people tagged.",
    icon: "📅",
    stats: "10k+ posts organized",
  },
  {
    id: "feature-2",
    title: "Smart Collections",
    description: "AI-powered grouping automatically creates albums from your photos based on events, locations, and faces.",
    icon: "🎨",
    stats: "6.4k photos curated",
  },
  {
    id: "feature-3",
    title: "Secure Download",
    description: "One-click download of your entire archive in a beautifully formatted ZIP file with encrypted storage.",
    icon: "🔒",
    stats: "97% satisfaction rate",
  },
];
