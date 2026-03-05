import { render, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import Hero from './Hero';

describe('Hero Component', () => {
  afterEach(() => {
    cleanup();
  });

  it('renders with default content', () => {
    const { getByTestId, getByRole } = render(<Hero />);

    expect(getByTestId('hero-section')).toBeInTheDocument();
    expect(getByRole('heading', { level: 1 })).toHaveTextContent('Orbital Forensics Platform');
    expect(getByRole('link', { name: /get started/i })).toBeInTheDocument();
  });

  it('renders custom headline and subheadline', () => {
    const { getByText } = render(
      <Hero
        headline="Custom Headline"
        subheadline="Custom subheadline text"
        ctaText="Launch"
      />
    );

    expect(getByText('Custom Headline')).toBeInTheDocument();
    expect(getByText('Custom subheadline text')).toBeInTheDocument();
    expect(getByText('Launch')).toBeInTheDocument();
  });

  it('calls onCtaClick when CTA is clicked', () => {
    const mockClick = vi.fn();
    const { getByRole } = render(<Hero onCtaClick={mockClick} />);

    const ctaButton = getByRole('link', { name: /get started/i });
    ctaButton.click();

    expect(mockClick).toHaveBeenCalledTimes(1);
  });

  it('has proper accessibility attributes', () => {
    const { container } = render(<Hero />);

    // Check for aria-label on status indicator
    const statusLabel = container.querySelector('[aria-label*="System status"]');
    expect(statusLabel).toBeInTheDocument();
  });
});
