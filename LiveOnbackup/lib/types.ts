export interface Testimonial {
  id: string;
  name: string;
  role: string;
  quote: string;
  avatar: string;
  rating: number;
  highlightImages: [string, string];
}

export interface Logo {
  name: string;
  src: string;
}

export interface FeatureCard {
  id: string;
  title: string;
  description: string;
  icon: string;
  stats: string;
}
