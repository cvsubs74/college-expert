import React from 'react';

/**
 * BackgroundBlobs - Organic floating shapes for Stratia's warm aesthetic
 * Creates subtle, large blobs in sage/beige tones that animate gently
 * Following M3 guidelines for creating depth without harsh shadows
 */
const BackgroundBlobs = () => {
    return (
        <div className="stratia-bg-blobs" aria-hidden="true">
            {/* Large sage blob - top right */}
            <div className="stratia-blob stratia-blob-1 animate-pulse-soft" />

            {/* Medium terracotta blob - bottom left */}
            <div
                className="stratia-blob stratia-blob-2 animate-pulse-soft"
                style={{ animationDelay: '2s' }}
            />

            {/* Small sage blob - center right */}
            <div
                className="stratia-blob stratia-blob-3 animate-pulse-soft"
                style={{ animationDelay: '4s' }}
            />
        </div>
    );
};

export default BackgroundBlobs;
