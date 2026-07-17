"use client";

interface RadarProps {
  data: { label: string; value: number }[];
  size?: number;
}

export default function RadarChart({ data, size = 280 }: RadarProps) {
  if (data.length === 0) return null;
  const cx = size / 2, cy = size / 2, r = size * 0.38;
  const n = data.length;
  const angleStep = (2 * Math.PI) / n;

  const getPoint = (i: number, val: number) => {
    const angle = i * angleStep - Math.PI / 2;
    return { x: cx + r * val * Math.cos(angle), y: cy + r * val * Math.sin(angle) };
  };

  const rings = [0.25, 0.5, 0.75, 1.0].map((scale) => {
    const pts = Array.from({ length: n }, (_, i) => {
      const p = getPoint(i, scale);
      return `${p.x},${p.y}`;
    }).join(" ");
    return <polygon key={scale} points={pts} fill="none" stroke="#e5e7eb" strokeWidth="1" />;
  });

  const axes = Array.from({ length: n }, (_, i) => {
    const p = getPoint(i, 1);
    return <line key={`axis-${i}`} x1={cx} y1={cy} x2={p.x} y2={p.y} stroke="#e5e7eb" strokeWidth="1" />;
  });

  const dataPts = Array.from({ length: n }, (_, i) => {
    const p = getPoint(i, data[i].value);
    return `${p.x},${p.y}`;
  }).join(" ");

  const labels = data.map((d, i) => {
    const p = getPoint(i, 1.15);
    return (
      <text key={`label-${i}`} x={p.x} y={p.y} textAnchor="middle" dominantBaseline="middle"
            className="fill-gray-600" fontSize="11" fontFamily="system-ui">
        {d.label.length > 5 ? d.label.slice(0, 5) + "…" : d.label}
      </text>
    );
  });

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      {rings}{axes}
      <polygon points={dataPts} fill="rgba(168,85,247,0.2)" stroke="#a855f7" strokeWidth="2" />
      {labels}
    </svg>
  );
}
