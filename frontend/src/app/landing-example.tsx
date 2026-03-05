/**
 * Landing Page Example
 *
 * This demonstrates how to use the Hero component in a Next.js page.
 * Copy this pattern to your actual landing page route.
 */

import Hero from '@/components/Hero';

export default function LandingExample() {
  return (
    <div className="landing-page">
      <Hero
        headline="Shopify Multi-Supplier Platform"
        subheadline="Automate inventory management across 8+ vendors with deep-space precision"
        ctaText="Get Started"
        ctaHref="/auth/login"
      />

      {/* Additional sections would go here */}
      {/* Features, pricing, testimonials, etc. */}
    </div>
  );
}
