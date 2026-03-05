import Hero from '@/components/Hero';

export default function HeroDemoPage() {
  return (
    <div style={{ margin: 0, padding: 0, width: '100vw', height: '100vh', overflow: 'auto' }}>
      <Hero
        headline="Shopify Multi-Supplier Platform"
        subheadline="Automate inventory management across 8+ vendors with deep-space precision"
        ctaText="Get Started"
        ctaHref="/auth/login"
      />
    </div>
  );
}
