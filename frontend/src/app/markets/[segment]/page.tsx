import { MarketSegmentTerminal } from '@/components/markets/MarketSegmentTerminal';
import { getSegmentDefinition, type MarketSegment } from '@/lib/segments';

export default async function MarketSegmentPage({
  params,
}: {
  params: Promise<{ segment: string }>;
}) {
  const { segment } = await params;
  const definition = getSegmentDefinition(segment);

  if (!definition) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-950 text-slate-200">
        Unsupported market segment.
      </div>
    );
  }

  return <MarketSegmentTerminal segment={definition.slug as MarketSegment} />;
}
