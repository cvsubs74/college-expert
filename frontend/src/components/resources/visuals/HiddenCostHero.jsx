import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

// Hero infographic for "The Hidden Cost of College Research."
//
// A 12-hour clock face. Each segment represents a research dimension a
// student has to hunt down per university. As the user scrolls into view,
// segments fill sequentially with a sweeping motion (think: clock hand
// moving around the dial), and the center label counts up to 35 hours.
//
// Design intent:
//   - The clock metaphor is the headline visual: time is the cost we're
//     measuring, and it's literally being "spent" as the segments fill.
//   - Each filled segment shows the research dimension on the rim; the
//     center holds the running total that grows as segments fill.
//   - Animation duration is intentionally generous (~3s) so a viewer
//     scrolling past has time to register the buildup.

const DIMENSIONS = [
    { label: 'Degrees', minutes: 25 },
    { label: 'Deadlines', minutes: 20 },
    { label: 'Supplements', minutes: 35 },
    { label: 'Aid', minutes: 30 },
    { label: 'Scholarships', minutes: 35 },
    { label: 'Test policy', minutes: 15 },
    { label: 'Demonstrated interest', minutes: 20 },
    { label: 'Location & fit', minutes: 25 },
    { label: 'Alumni network', minutes: 15 },
    { label: 'Athletics', minutes: 20 },
    { label: 'Application platform', minutes: 15 },
    { label: 'Visit & contact', minutes: 25 },
];

const TOTAL_MINUTES = DIMENSIONS.reduce((s, d) => s + d.minutes, 0); // ~280
// Compounded across ~10 schools (the marketing figure rounds to 35h):
const TOTAL_HOURS_HEADLINE = 35;

const polarToCartesian = (cx, cy, r, angleDeg) => {
    const angleRad = ((angleDeg - 90) * Math.PI) / 180;
    return {
        x: cx + r * Math.cos(angleRad),
        y: cy + r * Math.sin(angleRad),
    };
};

const arcPath = (cx, cy, rOuter, rInner, startAngle, endAngle) => {
    const startOuter = polarToCartesian(cx, cy, rOuter, endAngle);
    const endOuter = polarToCartesian(cx, cy, rOuter, startAngle);
    const startInner = polarToCartesian(cx, cy, rInner, startAngle);
    const endInner = polarToCartesian(cx, cy, rInner, endAngle);
    const largeArc = endAngle - startAngle <= 180 ? 0 : 1;
    return [
        `M ${startOuter.x} ${startOuter.y}`,
        `A ${rOuter} ${rOuter} 0 ${largeArc} 0 ${endOuter.x} ${endOuter.y}`,
        `L ${startInner.x} ${startInner.y}`,
        `A ${rInner} ${rInner} 0 ${largeArc} 1 ${endInner.x} ${endInner.y}`,
        'Z',
    ].join(' ');
};

const HiddenCostHero = () => {
    const ref = useRef(null);
    const inView = useInView(ref, { once: true, margin: '-10% 0px' });

    const cx = 220;
    const cy = 220;
    const rOuter = 180;
    const rInner = 110;
    const segCount = DIMENSIONS.length;
    const segAngle = 360 / segCount;

    return (
        <div
            ref={ref}
            className="relative w-full max-w-[520px] mx-auto py-6"
            aria-label="Clock infographic showing twelve research dimensions per university"
        >
            <svg
                viewBox="0 0 440 440"
                className="w-full h-auto drop-shadow-sm"
                role="img"
            >
                {/* Outer faint ring */}
                <circle
                    cx={cx}
                    cy={cy}
                    r={rOuter + 8}
                    fill="none"
                    stroke="#E0DED8"
                    strokeWidth="1"
                />

                {/* Hour-segment slots (background) */}
                {DIMENSIONS.map((_, i) => {
                    const start = i * segAngle;
                    const end = start + segAngle - 1.5; // gap between segments
                    return (
                        <path
                            key={`bg-${i}`}
                            d={arcPath(cx, cy, rOuter, rInner, start, end)}
                            fill="#F8F6F0"
                            stroke="#E0DED8"
                            strokeWidth="1"
                        />
                    );
                })}

                {/* Filled segments — animate in sequentially */}
                {DIMENSIONS.map((dim, i) => {
                    const start = i * segAngle;
                    const end = start + segAngle - 1.5;
                    const path = arcPath(cx, cy, rOuter, rInner, start, end);
                    return (
                        <motion.path
                            key={`fg-${i}`}
                            d={path}
                            fill="url(#segmentGradient)"
                            initial={{ opacity: 0 }}
                            animate={inView ? { opacity: 1 } : { opacity: 0 }}
                            transition={{
                                duration: 0.25,
                                delay: 0.25 + i * 0.18,
                                ease: 'easeOut',
                            }}
                        />
                    );
                })}

                {/* Segment labels on the rim */}
                {DIMENSIONS.map((dim, i) => {
                    const labelAngle = i * segAngle + segAngle / 2;
                    const labelR = rOuter + 24;
                    const { x, y } = polarToCartesian(cx, cy, labelR, labelAngle);
                    return (
                        <motion.text
                            key={`lbl-${i}`}
                            x={x}
                            y={y}
                            fontSize="10"
                            fontWeight="500"
                            fill="#4A4A4A"
                            textAnchor="middle"
                            dominantBaseline="middle"
                            initial={{ opacity: 0 }}
                            animate={inView ? { opacity: 1 } : { opacity: 0 }}
                            transition={{ duration: 0.4, delay: 0.4 + i * 0.18 }}
                        >
                            {dim.label}
                        </motion.text>
                    );
                })}

                {/* Center: total hours */}
                <motion.text
                    x={cx}
                    y={cy - 14}
                    fontSize="56"
                    fontWeight="800"
                    fill="#1A4D2E"
                    textAnchor="middle"
                    dominantBaseline="middle"
                    initial={{ opacity: 0, scale: 0.6 }}
                    animate={inView ? { opacity: 1, scale: 1 } : { opacity: 0, scale: 0.6 }}
                    transition={{
                        duration: 0.6,
                        delay: 0.25 + segCount * 0.18 + 0.2,
                        type: 'spring',
                        stiffness: 200,
                    }}
                >
                    ~{TOTAL_HOURS_HEADLINE}h
                </motion.text>
                <motion.text
                    x={cx}
                    y={cy + 22}
                    fontSize="13"
                    fontWeight="500"
                    fill="#6B6B6B"
                    textAnchor="middle"
                    dominantBaseline="middle"
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : { opacity: 0 }}
                    transition={{ duration: 0.4, delay: 0.25 + segCount * 0.18 + 0.4 }}
                >
                    of manual research
                </motion.text>
                <motion.text
                    x={cx}
                    y={cy + 42}
                    fontSize="11"
                    fontWeight="400"
                    fill="#8A8A8A"
                    textAnchor="middle"
                    dominantBaseline="middle"
                    initial={{ opacity: 0 }}
                    animate={inView ? { opacity: 1 } : { opacity: 0 }}
                    transition={{ duration: 0.4, delay: 0.25 + segCount * 0.18 + 0.55 }}
                >
                    per applicant
                </motion.text>

                {/* Gradient def */}
                <defs>
                    <linearGradient id="segmentGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                        <stop offset="0%" stopColor="#2D6B45" />
                        <stop offset="100%" stopColor="#1A4D2E" />
                    </linearGradient>
                </defs>
            </svg>

            {/* Caption beneath the clock */}
            <p className="text-center text-sm text-[#6B6B6B] mt-2 italic">
                Twelve research dimensions × ~10 schools. The clock fills as the work piles up.
            </p>
        </div>
    );
};

export default HiddenCostHero;
