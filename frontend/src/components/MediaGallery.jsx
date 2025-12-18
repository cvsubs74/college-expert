import React, { useState, useRef, useEffect } from 'react';
import {
    PhotoIcon,
    FilmIcon,
    ArrowsPointingOutIcon,
    ArrowDownTrayIcon,
    PlayIcon,
    XMarkIcon,
    ChevronLeftIcon,
    ChevronRightIcon
} from '@heroicons/react/24/outline';

/**
 * MediaGallery - Beautiful carousel for university visual content
 * Displays infographics and videos in a unified, immersive carousel
 */
const MediaGallery = ({ media }) => {
    const [selectedImage, setSelectedImage] = useState(null);
    const [playingVideoIdx, setPlayingVideoIdx] = useState(null);  // Track by index, not id
    const [currentIndex, setCurrentIndex] = useState(0);
    const carouselRef = useRef(null);
    const videoRefs = useRef({});

    // Handle null/undefined media gracefully
    const { infographics = [], videos = [] } = media || {};

    // Combine infographics and videos into a single array with type markers
    const allMedia = [
        ...infographics.map(item => ({ ...item, type: 'infographic' })),
        ...videos.map(item => ({ ...item, type: 'video' }))
    ];

    const hasMedia = allMedia.length > 0;

    // Pause video when scrolling away from it, resume when coming back
    useEffect(() => {
        if (playingVideoIdx !== null) {
            const videoElement = videoRefs.current[playingVideoIdx];

            if (videoElement) {
                if (playingVideoIdx !== currentIndex) {
                    // We scrolled AWAY from the video - PAUSE it
                    videoElement.pause();
                } else {
                    // We're ON the video slide - PLAY it (if paused)
                    if (videoElement.paused) {
                        videoElement.play().catch(() => { }); // Catch autoplay policy errors
                    }
                }
            }
        }
    }, [currentIndex, playingVideoIdx]);

    if (!hasMedia) {
        return (
            <div className="bg-gradient-to-br from-gray-50 to-gray-100 rounded-2xl border-2 border-dashed border-gray-200 p-12 text-center">
                <PhotoIcon className="h-12 w-12 text-gray-300 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-500">No Visual Content Yet</h3>
                <p className="text-gray-400 text-sm mt-1">
                    Visual content for this university is coming soon.
                </p>
            </div>
        );
    }

    const scrollToIndex = (index) => {
        if (carouselRef.current) {
            const scrollWidth = carouselRef.current.scrollWidth;
            const itemWidth = scrollWidth / allMedia.length;
            carouselRef.current.scrollTo({
                left: itemWidth * index,
                behavior: 'smooth'
            });
            setCurrentIndex(index);
        }
    };

    const scrollPrev = () => {
        const newIndex = Math.max(0, currentIndex - 1);
        scrollToIndex(newIndex);
    };

    const scrollNext = () => {
        const newIndex = Math.min(allMedia.length - 1, currentIndex + 1);
        scrollToIndex(newIndex);
    };

    return (
        <div className="relative">
            {/* Main Carousel Container */}
            <div className="relative bg-gradient-to-br from-gray-50 via-white to-gray-100 rounded-2xl overflow-hidden border border-gray-200 shadow-sm">

                {/* Carousel Track */}
                <div
                    ref={carouselRef}
                    className="flex overflow-x-auto snap-x snap-mandatory scrollbar-hide"
                    style={{ scrollSnapType: 'x mandatory' }}
                    onScroll={(e) => {
                        const index = Math.round(e.target.scrollLeft / (e.target.scrollWidth / allMedia.length));
                        setCurrentIndex(index);
                    }}
                >
                    {allMedia.map((item, idx) => (
                        <div
                            key={item.id || idx}
                            className="flex-shrink-0 w-full snap-center p-4"
                        >
                            {item.type === 'infographic' ? (
                                // Infographic Card
                                <div
                                    className="group relative mx-auto max-w-5xl cursor-pointer"
                                    onClick={() => setSelectedImage(item)}
                                >
                                    <div className="relative rounded-2xl overflow-hidden shadow-xl bg-white">
                                        <img
                                            src={item.url}
                                            alt={item.title}
                                            className="w-full h-[500px] md:h-[650px] object-contain bg-gray-50"
                                            loading="lazy"
                                        />
                                        {/* Hover Overlay */}
                                        <div className="absolute inset-0 bg-black/0 group-hover:bg-black/40 transition-all duration-300 flex items-center justify-center">
                                            <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex flex-col items-center gap-2">
                                                <div className="p-4 bg-white rounded-full shadow-lg">
                                                    <ArrowsPointingOutIcon className="h-8 w-8 text-gray-900" />
                                                </div>
                                                <span className="text-white font-medium">Click to expand</span>
                                            </div>
                                        </div>
                                    </div>
                                    {/* Title */}
                                    <div className="mt-4 text-center">
                                        <h4 className="text-gray-900 font-semibold text-lg">{item.title}</h4>
                                    </div>
                                </div>
                            ) : (
                                // Video Card
                                <div className="relative mx-auto max-w-5xl">
                                    <div className="relative rounded-2xl overflow-hidden shadow-xl bg-black" style={{ minHeight: '500px' }}>
                                        {playingVideoIdx === idx ? (
                                            <video
                                                ref={(el) => { videoRefs.current[idx] = el; }}
                                                src={item.url}
                                                controls
                                                autoPlay
                                                className="w-full h-full"
                                            >
                                                Your browser does not support video playback.
                                            </video>
                                        ) : (
                                            <>
                                                {item.thumbnail && (
                                                    <img
                                                        src={item.thumbnail}
                                                        alt={item.title}
                                                        className="w-full h-full object-cover"
                                                    />
                                                )}
                                                <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                                                    <button
                                                        onClick={() => setPlayingVideoIdx(idx)}
                                                        className="group p-6 bg-white/90 hover:bg-white rounded-full hover:scale-110 transition-all shadow-2xl"
                                                    >
                                                        <PlayIcon className="h-12 w-12 text-amber-600 group-hover:text-amber-700" />
                                                    </button>
                                                </div>
                                            </>
                                        )}
                                    </div>
                                    {/* Title */}
                                    <div className="mt-4 text-center">
                                        <h4 className="text-gray-900 font-semibold text-lg">{item.title}</h4>
                                        {item.duration && (
                                            <span className="text-sm text-gray-500">{item.duration}</span>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {/* Navigation Arrows */}
                {allMedia.length > 1 && (
                    <>
                        <button
                            onClick={scrollPrev}
                            disabled={currentIndex === 0}
                            className={`absolute left-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-white shadow-lg border border-gray-200 hover:bg-gray-50 transition-all ${currentIndex === 0 ? 'opacity-30 cursor-not-allowed' : 'opacity-100'
                                }`}
                        >
                            <ChevronLeftIcon className="h-6 w-6 text-gray-700" />
                        </button>
                        <button
                            onClick={scrollNext}
                            disabled={currentIndex === allMedia.length - 1}
                            className={`absolute right-4 top-1/2 -translate-y-1/2 p-3 rounded-full bg-white shadow-lg border border-gray-200 hover:bg-gray-50 transition-all ${currentIndex === allMedia.length - 1 ? 'opacity-30 cursor-not-allowed' : 'opacity-100'
                                }`}
                        >
                            <ChevronRightIcon className="h-6 w-6 text-gray-700" />
                        </button>
                    </>
                )}

                {/* Pagination Dots */}
                {allMedia.length > 1 && (
                    <div className="flex justify-center gap-2 pb-6">
                        {allMedia.map((item, idx) => (
                            <button
                                key={idx}
                                onClick={() => scrollToIndex(idx)}
                                className={`transition-all duration-300 rounded-full ${currentIndex === idx
                                    ? 'w-8 h-3 bg-amber-500'
                                    : 'w-3 h-3 bg-gray-300 hover:bg-gray-400'
                                    }`}
                            />
                        ))}
                    </div>
                )}
            </div>

            {/* Image Lightbox */}
            {selectedImage && (
                <div
                    className="fixed inset-0 bg-black/95 z-50 flex items-center justify-center p-4 md:p-8"
                    onClick={() => setSelectedImage(null)}
                >
                    <button
                        onClick={() => setSelectedImage(null)}
                        className="absolute top-4 right-4 p-3 bg-white/10 hover:bg-white/20 rounded-full text-white transition-colors z-10"
                    >
                        <XMarkIcon className="h-6 w-6" />
                    </button>
                    <div className="max-w-6xl max-h-[90vh] relative" onClick={(e) => e.stopPropagation()}>
                        <img
                            src={selectedImage.url}
                            alt={selectedImage.title}
                            className="max-w-full max-h-[85vh] object-contain rounded-lg shadow-2xl"
                        />
                        <div className="absolute bottom-0 left-0 right-0 p-6 bg-gradient-to-t from-black/90 via-black/60 to-transparent rounded-b-lg">
                            <h3 className="text-white font-semibold text-xl">{selectedImage.title}</h3>
                            <a
                                href={selectedImage.url}
                                download
                                className="inline-flex items-center gap-2 mt-3 px-4 py-2 bg-white/20 hover:bg-white/30 rounded-xl text-white text-sm font-medium transition-colors"
                            >
                                <ArrowDownTrayIcon className="h-4 w-4" />
                                Download Full Size
                            </a>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default MediaGallery;
