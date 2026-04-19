export type MarketSegment = 'crypto';

export interface SegmentDefinition {
  slug: MarketSegment;
  label: string;
  icon: string;
  accent: string;
  backendMarket: string;
  route: string;
  headline: string;
}

export const MARKET_SEGMENTS: SegmentDefinition[] = [
  {
    slug: 'crypto',
    label: 'Crypto Microstructure',
    icon: 'CR',
    accent: 'cyan',
    backendMarket: 'CRYPTO',
    route: '/markets/crypto',
    headline: 'Crypto-only HITL terminal with HMM regime filtering, IPDA context, OTE gating, and order-flow-aware execution.',
  },
];

export function getSegmentDefinition(segment: string) {
  return MARKET_SEGMENTS.find((item) => item.slug === segment);
}

export function inferSegmentFromMarket(): MarketSegment {
  return 'crypto';
}

export function inferSegmentFromSymbol(): MarketSegment {
  return 'crypto';
}
